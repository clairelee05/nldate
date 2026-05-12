from __future__ import annotations

import calendar
import re
from dataclasses import dataclass
from datetime import date, timedelta


class ParseError(ValueError):
    """Raised when a date expression cannot be parsed."""


_MONTHS = {month.lower(): idx for idx, month in enumerate(calendar.month_name) if month}
_MONTHS |= {month.lower(): idx for idx, month in enumerate(calendar.month_abbr) if month}
_WEEKDAYS = {day.lower(): idx for idx, day in enumerate(calendar.day_name)}
_WEEKDAYS |= {day.lower()[:3]: idx for idx, day in enumerate(calendar.day_name)}
_NUM_WORDS = {"zero": 0, "one": 1, "a": 1, "an": 1,"two": 2,"three": 3,"four": 4,"five": 5,
              "six": 6,"seven": 7,"eight": 8,"nine": 9,"ten": 10,"eleven": 11,"twelve": 12,
              "thirteen": 13,"fourteen": 14,"fifteen": 15,"sixteen": 16,"seventeen": 17,
              "eighteen": 18,"nineteen": 19,"twenty": 20,"thirty": 30,"forty": 40,"fifty": 50,
              "sixty": 60,"seventy": 70,"eighty": 80,"ninety": 90,}
_UNIT_RE = r"years?|months?|weeks?|days?"
_OFFSET_RE = re.compile(
    rf"(?P<num>\d+|[a-z]+(?:-[a-z]+)?)\s+(?P<unit>{_UNIT_RE})",
    re.IGNORECASE,
)
_DATE_NUMERIC_RE = re.compile(r"^(?P<m>\d{1,2})/(?P<d>\d{1,2})(?:/(?P<y>\d{2,4}))?$")
_DATE_ISO_RE = re.compile(r"^(?P<y>\d{4})-(?P<m>\d{1,2})-(?P<d>\d{1,2})$")
_MONTH_DATE_RE = re.compile(
    r"^(?P<month>[a-z]+)\s+(?P<day>\d{1,2})(?:st|nd|rd|th)?(?:,?\s+(?P<year>\d{4}))?$",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Offset:
    years: int = 0
    months: int = 0
    weeks: int = 0
    days: int = 0

    def signed(self, sign: int) -> Offset:
        return Offset(
            years=sign * self.years,
            months=sign * self.months,
            weeks=sign * self.weeks,
            days=sign * self.days,
        )


def parse(s: str, today: date | None = None) -> date:
    ref = today or date.today()
    text = _normalize(s)
    if not text:
        raise ParseError("date expression is empty")
    return _parse_expr(text, ref)


def _normalize(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower().replace(",", "")).replace(" from now", "")


def _parse_expr(text: str, today: date) -> date:
    if text in {"today", "now"}:
        return today
    if text == "tomorrow":
        return today + timedelta(days=1)
    if text == "yesterday":
        return today - timedelta(days=1)

    weekday = _parse_weekday_expr(text, today)
    if weekday is not None:
        return weekday

    relative = _parse_standalone_relative(text, today)
    if relative is not None:
        return relative

    anchored = _parse_anchored_offset(text, today)
    if anchored is not None:
        return anchored

    absolute = _parse_absolute(text, today)
    if absolute is not None:
        return absolute

    raise ParseError(f"could not parse date expression: {text!r}")


def _parse_weekday_expr(text: str, today: date) -> date | None:
    match = re.fullmatch(r"(?:(next|last|this) )?([a-z]+)", text)
    if match is None:
        return None
    modifier, day_name = match.groups()
    target = _WEEKDAYS.get(day_name)
    if target is None:
        return None

    delta = target - today.weekday()
    if modifier == "next":
        delta += 7 if delta <= 0 else 0
    elif modifier == "last":
        delta -= 7 if delta >= 0 else 0
    elif modifier == "this" or modifier is None:
        delta += 7 if delta < 0 else 0
    return today + timedelta(days=delta)


def _parse_standalone_relative(text: str, today: date) -> date | None:
    if match := re.fullmatch(r"in (.+)", text):
        return _apply_offset(today, _parse_offset(match.group(1)))
    if match := re.fullmatch(r"(.+) ago", text):
        return _apply_offset(today, _parse_offset(match.group(1)).signed(-1))
    if match := re.fullmatch(r"(.+) (?:after|from) today", text):
        return _apply_offset(today, _parse_offset(match.group(1)))
    if match := re.fullmatch(r"(.+) before today", text):
        return _apply_offset(today, _parse_offset(match.group(1)).signed(-1))
    return None


def _parse_anchored_offset(text: str, today: date) -> date | None:
    # Try both separators because the anchor can itself be relative, e.g.
    # "1 year and 2 months after yesterday".
    for sep, sign in ((" after ", 1), (" before ", -1), (" from ", 1)):
        if sep not in text:
            continue
        left, right = text.split(sep, 1)
        try:
            offset = _parse_offset(left).signed(sign)
            anchor = _parse_expr(right, today)
        except ParseError:
            continue
        return _apply_offset(anchor, offset)
    return None


def _parse_absolute(text: str, today: date) -> date | None:
    if match := _DATE_ISO_RE.fullmatch(text):
        return date(int(match.group("y")), int(match.group("m")), int(match.group("d")))

    if match := _DATE_NUMERIC_RE.fullmatch(text):
        year_text = match.group("y")
        year = today.year if year_text is None else _expand_year(int(year_text))
        return date(year, int(match.group("m")), int(match.group("d")))

    if match := _MONTH_DATE_RE.fullmatch(text):
        month = _MONTHS.get(match.group("month"))
        if month is None:
            return None
        year = int(match.group("year") or today.year)
        return date(year, month, int(match.group("day")))

    return None


def _parse_offset(text: str) -> Offset:
    cleaned = text.replace(",", " ").replace(" and ", " ")
    years = months = weeks = days = 0
    position = 0
    saw_match = False
    for match in _OFFSET_RE.finditer(cleaned):
        if cleaned[position : match.start()].strip():
            raise ParseError(f"invalid offset: {text!r}")
        amount = _parse_int(match.group("num"))
        unit = match.group("unit").rstrip("s").lower()
        if unit == "year":
            years += amount
        elif unit == "month":
            months += amount
        elif unit == "week":
            weeks += amount
        elif unit == "day":
            days += amount
        else:  # pragma: no cover - regex constrains this
            raise ParseError(f"unknown offset unit: {unit!r}")
        saw_match = True
        position = match.end()
    if not saw_match or cleaned[position:].strip():
        raise ParseError(f"invalid offset: {text!r}")
    return Offset(years=years, months=months, weeks=weeks, days=days)


def _parse_int(text: str) -> int:
    if text.isdigit():
        return int(text)
    if "-" in text:
        total = sum(_NUM_WORDS.get(part, -10_000) for part in text.split("-"))
        if total >= 0:
            return total
    if text in _NUM_WORDS:
        return _NUM_WORDS[text]
    raise ParseError(f"invalid number: {text!r}")


def _apply_offset(start: date, offset: Offset) -> date:
    shifted = _add_months(start, offset.years * 12 + offset.months)
    return shifted + timedelta(weeks=offset.weeks, days=offset.days)


def _add_months(start: date, months: int) -> date:
    month_index = start.month - 1 + months
    year = start.year + month_index // 12
    month = month_index % 12 + 1
    day = min(start.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def _expand_year(year: int) -> int:
    if year < 100:
        return 2000 + year
    return year
