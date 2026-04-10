from __future__ import annotations

from datetime import time


TIME_FORMAT = "%H:%M:%S"


def parse_time_string(value: str) -> time | None:
    try:
        parts = str(value).strip().split(":")
        if len(parts) != 3:
            return None
        hour, minute, second = (int(part) for part in parts)
        return time(hour, minute, second)
    except (TypeError, ValueError):
        return None


def format_time_string(value: time) -> str:
    return value.strftime(TIME_FORMAT)


def is_valid_time_string(value: str) -> bool:
    return parse_time_string(value) is not None


def normalize_time_string(value: str, fallback: str) -> str:
    parsed = parse_time_string(value)
    if parsed is None:
        parsed = parse_time_string(fallback)
    if parsed is None:
        raise ValueError(f"Invalid fallback time string: {fallback}")
    return format_time_string(parsed)
