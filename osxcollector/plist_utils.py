"""Plist reading via stdlib plistlib."""

from __future__ import annotations

import os
import plistlib
from typing import Any

from osxcollector.logging_jsonl import Logger
from osxcollector.normalize import normalize_val


def read_plist(plist_path: str, default: Any = None) -> Any:
    """Read a plist file and return a JSON-friendly structure."""
    if default is None:
        default = {}

    if not os.path.isfile(plist_path):
        Logger.log_warning(f"plist file not found. plist_path[{plist_path}]")
        return default

    try:
        if os.path.getsize(plist_path) == 0:
            Logger.log_warning(f"Empty plist. plist_path[{plist_path}]")
            return default

        with open(plist_path, "rb") as handle:
            raw = handle.read()
        if not raw:
            Logger.log_warning(f"Empty plist. plist_path[{plist_path}]")
            return default

        try:
            plist_dictionary = plistlib.loads(raw)
        except Exception as parse_error:
            Logger.log_error(
                f"Unable to parse plist: [{parse_error}]. plist_path[{plist_path}]",
            )
            return default

        plist = normalize_val(plist_dictionary)
        if not isinstance(plist, (dict, list)):
            Logger.log_error(
                f"plist is wrong type. plist_path[{plist_path}] type[{type(plist).__name__}]",
            )
            return default
        return plist
    except OSError as read_plist_e:
        Logger.log_exception(read_plist_e, message=f"read_plist failed on {plist_path}")
    return default
