from __future__ import annotations


def parse_time(value: str) -> int:
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def format_time(minutes: int) -> str:
    minutes = round(minutes)
    hours = (minutes // 60) % 24
    mins = minutes % 60
    day_offset = minutes // (24 * 60)
    suffix = f" +{day_offset}d" if day_offset else ""
    return f"{hours:02d}:{mins:02d}{suffix}"
