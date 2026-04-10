from __future__ import annotations

from datetime import date


DATE_FORMAT = "%Y-%m-%d"


def parse_date_string(value: str) -> date | None:
    try:
        parts = str(value).strip().split("-")
        if len(parts) != 3:
            return None
        year, month, day = (int(part) for part in parts)
        return date(year, month, day)
    except (TypeError, ValueError):
        return None


def format_date_string(value: date) -> str:
    return value.strftime(DATE_FORMAT)


def is_valid_date_string(value: str) -> bool:
    return parse_date_string(value) is not None


def normalize_date_string(value: str, fallback: str) -> str:
    parsed = parse_date_string(value)
    if parsed is None:
        parsed = parse_date_string(fallback)
    if parsed is None:
        raise ValueError(f"Invalid fallback date string: {fallback}")
    return format_date_string(parsed)
