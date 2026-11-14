import datetime as dt

import pytest

from app import scoring

AS_OF = dt.date(2026, 6, 30)


def score(sector, e, s, g, events=()):
    return scoring.score_company(sector, e, s, g, events, AS_OF)


@pytest.mark.parametrize("weights", [*scoring.SECTOR_WEIGHTS.values(), scoring.DEFAULT_WEIGHTS])
def test_weights_sum_to_one_with_governance_floor(weights):
    assert sum(weights) == pytest.approx(1.0)
    assert weights[2] >= scoring.GOVERNANCE_WEIGHT_FLOOR


@pytest.mark.parametrize(
    ("score_value", "grade"),
    [
        (100, "AAA"), (85.7, "AAA"), (85.6, "AA"), (71.4, "AA"), (71.3, "A"), (57.1, "A"),
        (57.0, "BBB"), (42.9, "BBB"), (42.8, "BB"), (28.6, "BB"), (28.5, "B"), (14.3, "B"),
        (14.2, "CCC"), (0, "CCC"),
    ],
)
def test_msci_seven_equal_grade_bands(score_value, grade):
    assert scoring.grade_for_score(score_value) == grade


def test_sector_weights_drive_weighted_pillar_score():
    assert score("Energy", 100, 0, 0).weighted_pillar_score == 45.0
    assert score("Financials", 100, 0, 0).weighted_pillar_score == 12.0


def test_unknown_sector_falls_back_to_defaults():
    assert scoring.pillar_weights("Space Mining") == scoring.DEFAULT_WEIGHTS
    assert scoring.sector_benchmark("Space Mining") == scoring.DEFAULT_BENCHMARK


def test_industry_adjustment_rescales_and_clips_to_benchmark():
    lo, hi = scoring.sector_benchmark("Technology")
    mid = (lo + hi) / 2

    assert score("Technology", mid, mid, mid).composite_score == 50.0
    assert score("Technology", 100, 100, 100).composite_score == 100.0
    assert score("Technology", 0, 0, 0).composite_score == 0.0


def test_same_pillars_grade_differently_by_industry():
    # A 50 is weak for a utility but decent for an energy company.
    assert score("Energy", 50, 50, 50).composite_score > score("Utilities", 50, 50, 50).composite_score


def test_sector_percentile():
    assert scoring.sector_percentile(20, [10, 20, 30]) == 66.7
    assert scoring.sector_percentile(30, [10, 20, 30]) == 100.0
    assert scoring.sector_percentile(50, []) == 50.0


@pytest.mark.parametrize(
    ("coverage", "spread", "level"),
    [(85, 8, "high"), (95, 9, "medium"), (84, 5, "medium"), (69, 5, "low"), (95, 16, "low"), (70, 15, "medium")],
)
def test_confidence_levels(coverage, spread, level):
    assert scoring.confidence(coverage, spread) == level


@pytest.mark.parametrize(("change", "label"), [(3, "improving"), (2.9, "stable"), (-2.9, "stable"), (-3, "worsening")])
def test_trend_label(change, label):
    assert scoring.trend_label(change) == label


def test_trend_sign_follows_pillar_change():
    before = scoring.score_company("Technology", 60, 60, 60, (), scoring.one_year_before(AS_OF))
    after = score("Technology", 70, 70, 70)

    assert scoring.trend_label(after.composite_score - before.composite_score) == "improving"


def test_one_year_before_handles_leap_day():
    assert scoring.one_year_before(dt.date(2028, 2, 29)) == dt.date(2027, 2, 28)
