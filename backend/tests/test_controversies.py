import datetime as dt

import pytest

from app import scoring

AS_OF = dt.date(2026, 6, 30)


def event(category, months_ago, title="Mock: event"):
    days = round(months_ago * scoring.DAYS_PER_MONTH)
    return scoring.Controversy(category, AS_OF - dt.timedelta(days=days), title)


@pytest.mark.parametrize(("months", "factor"), [(0, 1.0), (12, 0.5), (24, 0.25), (36, 0.125), (37, 0.0), (-1, 0.0)])
def test_decay_halves_yearly_and_drops_after_three_years(months, factor):
    assert scoring.decay(months) == pytest.approx(factor)


def test_penalty_uses_category_points_and_decay():
    bd = scoring.score_company("Technology", 90, 90, 90, [event(4, 0), event(2, 12)], AS_OF)

    assert bd.controversy_penalty == pytest.approx(10 + 1.5, abs=0.1)
    assert [e.category for e in bd.controversy_events] == [4, 2]  # newest first
    assert bd.controversy_events[1].decay_factor == pytest.approx(0.5, abs=0.01)


def test_penalty_is_capped_and_score_never_negative():
    bd = scoring.score_company("Technology", 50, 50, 50, [event(5, 0)] * 4, AS_OF)

    assert bd.controversy_penalty == scoring.MAX_CONTROVERSY_PENALTY
    assert bd.composite_score == 0.0


def test_old_and_future_events_are_ignored():
    bd = scoring.score_company("Technology", 70, 70, 70, [event(5, 40), event(5, -2)], AS_OF)

    assert bd.controversy_penalty == 0
    assert bd.controversy_events == ()


def test_recent_category_5_caps_grade_at_bb():
    bd = scoring.score_company("Technology", 100, 100, 100, [event(5, 6)], AS_OF)

    assert bd.grade_before_cap == "AAA"
    assert bd.grade == "BB"
    assert "category 5" in bd.grade_cap_reason


def test_category_5_older_than_a_year_does_not_cap():
    bd = scoring.score_company("Technology", 100, 100, 100, [event(5, 13)], AS_OF)

    assert bd.grade == bd.grade_before_cap
    assert bd.grade_cap_reason is None


def test_weak_governance_caps_grade_at_bbb():
    bd = scoring.score_company("Technology", 100, 100, 29, [], AS_OF)

    assert bd.grade_before_cap in ("AAA", "AA", "A")
    assert bd.grade == "BBB"
    assert "governance" in bd.grade_cap_reason


def test_stricter_cap_wins_and_cap_never_raises_a_grade():
    both = scoring.score_company("Technology", 100, 100, 29, [event(5, 1)], AS_OF)
    low = scoring.score_company("Technology", 40, 40, 29, [], AS_OF)

    assert both.grade == "BB"
    assert low.grade == low.grade_before_cap == "CCC"
    assert low.grade_cap_reason is None
