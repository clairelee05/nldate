from datetime import date

from nldate import parse

BASE = date(2026, 5, 11)


def test_today() -> None:
    assert parse("today", today=BASE) == BASE


def test_tomorrow() -> None:
    assert parse("tomorrow", today=BASE) == date(2026, 5, 12)


def test_yesterday() -> None:
    assert parse("yesterday", today=BASE) == date(2026, 5, 10)


def test_next_tuesday() -> None:
    assert parse("next Tuesday", today=BASE) == date(2026, 5, 12)


def test_last_tuesday() -> None:
    assert parse("last Tuesday", today=BASE) == date(2026, 5, 5)


def test_plain_weekday_is_this_week_or_today() -> None:
    assert parse("Monday", today=BASE) == BASE
    assert parse("Friday", today=BASE) == date(2026, 5, 15)


def test_absolute_month_day_year() -> None:
    assert parse("December 1st, 2025", today=BASE) == date(2025, 12, 1)


def test_absolute_iso() -> None:
    assert parse("2025-12-01", today=BASE) == date(2025, 12, 1)


def test_absolute_slash_us_order() -> None:
    assert parse("12/01/2025", today=BASE) == date(2025, 12, 1)


def test_days_before_absolute_date() -> None:
    assert parse("5 days before December 1st, 2025", today=BASE) == date(2025, 11, 26)


def test_year_and_month_after_yesterday() -> None:
    assert parse("1 year and 2 months after yesterday", today=BASE) == date(2027, 7, 10)


def test_in_three_days() -> None:
    assert parse("in 3 days", today=BASE) == date(2026, 5, 14)


def test_two_weeks_from_tomorrow_style_after() -> None:
    assert parse("two weeks after tomorrow", today=BASE) == date(2026, 5, 26)
    assert parse("two weeks from tomorrow", today=BASE) == date(2026, 5, 26)


def test_ago() -> None:
    assert parse("3 weeks ago", today=BASE) == date(2026, 4, 20)


def test_month_end_clamps() -> None:
    assert parse("1 month after January 31 2025", today=BASE) == date(2025, 2, 28)
