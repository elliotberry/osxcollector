"""Timestamp and value normalization for SQLite/plist values."""

from __future__ import annotations

import calendar
from datetime import datetime, timedelta
from numbers import Number
from typing import Any

from osxcollector.debug import debugbreak
from osxcollector.logging_jsonl import Logger

DATETIME_2001 = datetime(2001, 1, 1)
DATETIME_1970 = datetime(1970, 1, 1)
DATETIME_1601 = datetime(1601, 1, 1)
MIN_YEAR = 2004


def _timestamp_errorhandling(func):  # noqa: ANN001, ANN202
    def wrapper(*args: Any, **kwargs: Any) -> datetime | None:
        try:
            dt = func(*args, **kwargs)
            tomorrow = datetime.now() + timedelta(days=1)
            if dt.year < MIN_YEAR or dt > tomorrow:
                return None
            return dt
        except (OverflowError, OSError, TypeError, ValueError):
            return None

    return wrapper


def _convert_to_local(func):  # noqa: ANN001, ANN202
    def wrapper(*args: Any, **kwargs: Any) -> datetime:
        dt = func(*args, **kwargs)
        return datetime.fromtimestamp(calendar.timegm(dt.timetuple()))

    return wrapper


@_timestamp_errorhandling
@_convert_to_local
def seconds_since_2001_to_datetime(seconds: float) -> datetime:
    return DATETIME_2001 + timedelta(seconds=seconds)


@_timestamp_errorhandling
@_convert_to_local
def seconds_since_epoch_to_datetime(seconds: float) -> datetime:
    return DATETIME_1970 + timedelta(seconds=seconds)


@_timestamp_errorhandling
@_convert_to_local
def microseconds_since_epoch_to_datetime(microseconds: float) -> datetime:
    return DATETIME_1970 + timedelta(microseconds=microseconds)


@_timestamp_errorhandling
@_convert_to_local
def microseconds_since_1601_to_datetime(microseconds: float) -> datetime:
    return DATETIME_1601 + timedelta(microseconds=microseconds)


def value_to_datetime(val: Any) -> datetime | None:
    if isinstance(val, str):
        try:
            val = float(val)
        except ValueError:
            return None

    return (
        microseconds_since_epoch_to_datetime(val)
        or microseconds_since_1601_to_datetime(val)
        or seconds_since_epoch_to_datetime(val)
        or seconds_since_2001_to_datetime(val)
    )


def datetime_to_string(dt: datetime) -> str | None:
    try:
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except (OverflowError, ValueError):
        debugbreak()
        return None


def normalize_val(val: Any, key: str | None = None) -> Any:
    """Transform a SQLite/plist value into a JSON-serializable form."""
    if key and any(hint in key.lower() for hint in ["time", "utc", "date", "accessed"]):
        ts = value_to_datetime(val)
        if not ts and key in ["last_access_time", "expires_utc", "date_created", "end_time"]:
            ts = datetime.fromtimestamp(1)
        if ts:
            return datetime_to_string(ts)

    try:
        if isinstance(val, str):
            if key in ["rev_host", "scope"]:
                val = val.split(":")[0][::-1]
            return val
        if isinstance(val, bytes):
            try:
                return val.decode("utf-16le", errors="ignore")
            except Exception:
                return repr(val)
        if isinstance(val, memoryview):
            try:
                return bytes(val).decode("utf-16le", errors="ignore")
            except Exception:
                return repr(bytes(val))
        if isinstance(val, Number):
            return val
        if isinstance(val, dict):
            return {k: normalize_val(val.get(k), k) for k in val}
        if isinstance(val, (list, tuple)):
            return [normalize_val(stuff) for stuff in val]
        if not val:
            return ""
        debugbreak()
        return repr(val)
    except Exception as normalize_val_e:
        Logger.log_error(f"normalize_val: {normalize_val_e!r}")
        debugbreak()
        return repr(val)


# Compatibility aliases used by older tests / re-exports
_seconds_since_2001_to_datetime = seconds_since_2001_to_datetime
_seconds_since_epoch_to_datetime = seconds_since_epoch_to_datetime
_microseconds_since_epoch_to_datetime = microseconds_since_epoch_to_datetime
_microseconds_since_1601_to_datetime = microseconds_since_1601_to_datetime
_value_to_datetime = value_to_datetime
_datetime_to_string = datetime_to_string
_normalize_val = normalize_val
