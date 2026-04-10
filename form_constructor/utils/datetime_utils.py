from __future__ import annotations

from datetime import datetime


DATETIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_datetime_string(value: str) -> datetime | None:
    try:
        return datetime.strptime(str(value).strip(), DATETIME_FORMAT)
    except (TypeError, ValueError):
        return None


def format_datetime_string(value: datetime) -> str:
    return value.strftime(DATETIME_FORMAT)


def is_valid_datetime_string(value: str) -> bool:
    return parse_datetime_string(value) is not None


def normalize_datetime_string(value: str, fallback: str) -> str:
    parsed = parse_datetime_string(value)
    if parsed is None:
        parsed = parse_datetime_string(fallback)
    if parsed is None:
        raise ValueError(f"Invalid fallback datetime string: {fallback}")
    return format_datetime_string(parsed)
