"""File hashing, xattrs, and metadata."""

from __future__ import annotations

import base64
import os
import plistlib
from datetime import datetime
from functools import partial
from hashlib import md5, sha1, sha256
from typing import Any

from osxcollector.debug import debugbreak
from osxcollector.logging_jsonl import Logger
from osxcollector.macho import HAS_MACHOLIB, kyphosis
from osxcollector.normalize import datetime_to_string

ATTR_KMD_ITEM_WHERE_FROMS = "com.apple.metadata:kMDItemWhereFroms"
ATTR_QUARANTINE = "com.apple.quarantine"


def _hash_file(file_path: str) -> list[str]:
    hashers = [
        md5(usedforsecurity=False),
        sha1(usedforsecurity=False),
        sha256(),
    ]
    try:
        with open(file_path, "rb") as f:
            for chunk in iter(partial(f.read, 1024 * 1024), b""):
                for hasher in hashers:
                    hasher.update(chunk)
            return [hasher.hexdigest() for hasher in hashers]
    except OSError:
        debugbreak()
        return ["", "", ""]


def _get_xattr_bytes(file_path: str, attr: str) -> bytes | None:
    getxattr_fn = getattr(os, "getxattr", None)
    if getxattr_fn is not None:
        try:
            value = getxattr_fn(file_path, attr)
            return value if isinstance(value, bytes) else bytes(value)
        except OSError:
            return None
    try:
        from xattr import getxattr  # type: ignore[import-untyped]

        value = getxattr(file_path, attr)
        if isinstance(value, str):
            return value.encode("utf-8", errors="surrogateescape")
        if isinstance(value, bytes):
            return value
        return bytes(value)
    except Exception:
        return None


def get_extended_attr(file_path: str, attr: str) -> list[Any] | None:
    """Return extended attribute values as a list, or None if unset."""
    try:
        xattr_val = _get_xattr_bytes(file_path, attr)
        if xattr_val is None:
            return None
        if xattr_val.startswith(b"bplist"):
            try:
                plist_array = plistlib.loads(xattr_val)
                if isinstance(plist_array, list):
                    return list(plist_array)
                return [plist_array]
            except Exception as deserialize_plist_e:
                Logger.log_exception(
                    deserialize_plist_e,
                    message=f"get_extended_attr failed on {file_path} for {attr}",
                )
                return None
        try:
            return [xattr_val.decode("utf-8", errors="replace")]
        except Exception:
            return [repr(xattr_val)]
    except KeyError:
        return None
    except OSError:
        return None


def get_where_froms(file_path: str) -> list[Any] | None:
    return get_extended_attr(file_path, ATTR_KMD_ITEM_WHERE_FROMS)


def get_quarantines(file_path: str) -> list[Any] | None:
    return get_extended_attr(file_path, ATTR_QUARANTINE)


def get_file_info(file_path: str, log_xattr: bool = False) -> dict[str, Any]:
    """Gather hashes and timestamps for a file."""
    if not os.path.isfile(file_path):
        return {}

    atime = datetime_to_string(datetime.fromtimestamp(os.path.getatime(file_path)))
    mtime = datetime_to_string(datetime.fromtimestamp(os.path.getmtime(file_path)))
    ctime = datetime_to_string(datetime.fromtimestamp(os.path.getctime(file_path)))
    md5_hash, sha1_hash, sha2_hash = _hash_file(file_path)

    extra_data_check = ""
    extra_data_found = False
    if HAS_MACHOLIB:
        try:
            extra_data_result = str(kyphosis(file_path, False).extra_data)
            if extra_data_result != "{}":
                encoded = base64.b64encode(extra_data_result.encode("utf-8", errors="replace"))
                extra_data_check = encoded.decode("ascii")
                extra_data_found = True
        except Exception:
            extra_data_check = ""

    file_info: dict[str, Any] = {
        "md5": md5_hash,
        "sha1": sha1_hash,
        "sha2": sha2_hash,
        "file_path": file_path,
        "atime": atime,
        "mtime": mtime,
        "ctime": ctime,
        "extra_data_check": extra_data_check,
        "extra_data_found": extra_data_found,
    }

    if log_xattr:
        where_from = get_where_froms(file_path)
        if where_from:
            file_info["xattr-wherefrom"] = where_from
        quarantines = get_quarantines(file_path)
        if quarantines:
            file_info["xattr-quarantines"] = quarantines

    return file_info


# Compatibility aliases
_get_file_info = get_file_info
_get_extended_attr = get_extended_attr
_get_where_froms = get_where_froms
_get_quarantines = get_quarantines
