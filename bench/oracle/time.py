"""Strict RFC3339 timestamp parsing for the independent Oracle."""
from __future__ import annotations

import datetime
import re


_RFC3339 = re.compile(
    r"^(?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})T"
    r"(?P<time>[0-9]{2}:[0-9]{2}:[0-9]{2})(?P<fraction>\.[0-9]+)?"
    r"(?P<zone>Z|[+-][0-9]{2}:[0-9]{2})$"
)


class TimestampError(ValueError):
    pass


def parse_rfc3339(value: object, field: str = "timestamp") -> datetime.datetime:
    if not isinstance(value, str) or not _RFC3339.fullmatch(value):
        raise TimestampError(f"{field} must be a timezone-aware RFC3339 timestamp")
    try:
        parsed = datetime.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise TimestampError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise TimestampError(f"{field} must include a timezone")
    return parsed.astimezone(datetime.timezone.utc)


def at_or_before(value: object, cutoff: object) -> bool:
    return parse_rfc3339(value) <= parse_rfc3339(cutoff)
