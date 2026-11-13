import pytest

from app import scoring


@pytest.mark.parametrize(
    ("score", "grade"),
    [(100, "AAA"), (85, "AAA"), (84.9, "AA"), (65, "A"), (55, "BBB"), (45, "BB"), (35, "B"), (34.9, "CCC"), (0, "CCC")],
)
def test_grade_bands(score, grade):
    assert scoring.grade_for_score(score) == grade


def test_sector_weights_drive_composite():
    energy = scoring.score_company("Energy", 100, 0, 0, 0)
    financials = scoring.score_company("Financials", 100, 0, 0, 0)

    assert energy.composite_score == 55.0  # Energy weights Environmental at 0.55
    assert financials.composite_score == 15.0  # Financials weights it at 0.15


def test_unknown_sector_falls_back_to_default_weights():
    assert scoring.pillar_weights("Space Mining") == scoring.DEFAULT_WEIGHTS
    assert scoring.score_company("Space Mining", 100, 0, 0, 0).composite_score == 40.0


def test_controversy_penalty_is_capped():
    bd = scoring.score_company("Technology", 90, 90, 90, controversy_severity=20)

    assert bd.controversy_penalty == scoring.MAX_CONTROVERSY_PENALTY
    assert bd.composite_score == 60.0


def test_composite_never_goes_below_zero():
    bd = scoring.score_company("Technology", 10, 10, 10, controversy_severity=10)

    assert bd.composite_score == 0.0
    assert bd.grade == "CCC"


def test_sector_percentile():
    assert scoring.sector_percentile(20, [10, 20, 30]) == 66.7
    assert scoring.sector_percentile(30, [10, 20, 30]) == 100.0
    assert scoring.sector_percentile(50, []) == 50.0
