import pandas as pd
import pytest

from app.quant import portfolio
from app.quant.config import RunConfig


def _selected(sectors):
    n = len(sectors)
    return pd.DataFrame({
        "ticker": [f"T{i}" for i in range(n)],
        "sector": sectors,
        "composite_score": [float(n - i) for i in range(n)],
        "rank": list(range(1, n + 1)),
    })


def test_caps_hold_after_dust_is_dropped_and_weights_renormalize():
    # Score-weighted: the tail name is dust, and dropping it re-inflates the rest.
    cfg = RunConfig(position_sizing_method="score_weighted", max_position_weight=0.30,
                    max_sector_weight=0.60, min_position_weight=0.05)
    sel = _selected(["A", "A", "B", "B", "C"])
    sel.loc[4, "composite_score"] = -50.0  # far below the rest -> tiny weight

    sized = portfolio.size_positions(sel, pd.DataFrame(), cfg)

    assert sized["weight"].sum() == pytest.approx(1.0)
    assert sized["weight"].max() <= 0.30 + 1e-9
    assert sized.groupby("sector")["weight"].sum().max() <= 0.60 + 1e-9
    assert (sized["weight"] >= 0.05).all()


def test_infeasible_caps_leave_cash_instead_of_breaching():
    cfg = RunConfig(position_sizing_method="equal_weight", max_position_weight=0.22,
                    max_sector_weight=1.0, min_position_weight=0.0)

    sized = portfolio.size_positions(_selected(["A", "B", "C"]), pd.DataFrame(), cfg)

    assert sized["weight"].max() <= 0.22 + 1e-9
    assert sized["weight"].sum() == pytest.approx(0.66)


def test_sector_cap_excess_moves_to_other_sectors():
    cfg = RunConfig(position_sizing_method="equal_weight", max_position_weight=0.5,
                    max_sector_weight=0.4, min_position_weight=0.0)

    sized = portfolio.size_positions(_selected(["A", "A", "A", "B", "C"]), pd.DataFrame(), cfg)
    by_sector = sized.groupby("sector")["weight"].sum()

    assert by_sector["A"] == pytest.approx(0.4)
    assert sized["weight"].sum() == pytest.approx(1.0)
    assert sized["weight"].max() <= 0.5 + 1e-9
