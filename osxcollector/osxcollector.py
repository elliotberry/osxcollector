"""Compatibility re-exports matching the historical osxcollector.osxcollector module API."""

from __future__ import annotations

from sqlite3 import OperationalError

from osxcollector import __version__
from osxcollector.archive import LogFileArchiver
from osxcollector.collectors.base import foreach_homedir
from osxcollector.collectors.collector import Collector
from osxcollector.debug import DEBUG_MODE, debugbreak
from osxcollector.dictutils import DictUtils
from osxcollector.fileinfo import _get_extended_attr, _get_file_info, _get_quarantines, _get_where_froms, _hash_file
from osxcollector.logging_jsonl import Logger
from osxcollector.macho import kyphosis
from osxcollector.normalize import (
    DATETIME_1601,
    DATETIME_1970,
    DATETIME_2001,
    MIN_YEAR,
    _datetime_to_string,
    _microseconds_since_1601_to_datetime,
    _microseconds_since_epoch_to_datetime,
    _normalize_val,
    _seconds_since_2001_to_datetime,
    _seconds_since_epoch_to_datetime,
    _value_to_datetime,
)
from osxcollector.paths import ROOT_PATH, HomeDir, _get_homedirs, listdir, pathjoin
from osxcollector.sqlite_utils import connect

_foreach_homedir = foreach_homedir

__all__ = [
    "DEBUG_MODE",
    "DATETIME_1601",
    "DATETIME_1970",
    "DATETIME_2001",
    "MIN_YEAR",
    "ROOT_PATH",
    "Collector",
    "DictUtils",
    "HomeDir",
    "LogFileArchiver",
    "Logger",
    "OperationalError",
    "__version__",
    "_datetime_to_string",
    "_foreach_homedir",
    "_get_extended_attr",
    "_get_file_info",
    "_get_homedirs",
    "_get_quarantines",
    "_get_where_froms",
    "_hash_file",
    "_microseconds_since_1601_to_datetime",
    "_microseconds_since_epoch_to_datetime",
    "_normalize_val",
    "_seconds_since_2001_to_datetime",
    "_seconds_since_epoch_to_datetime",
    "_value_to_datetime",
    "connect",
    "debugbreak",
    "kyphosis",
    "listdir",
    "pathjoin",
]
