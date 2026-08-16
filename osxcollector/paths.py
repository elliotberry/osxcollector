"""Path helpers built around a configurable filesystem root."""

from __future__ import annotations

import os
from collections import namedtuple

ROOT_PATH = "/"

HomeDir = namedtuple("HomeDir", ["user_name", "path"])


def listdir(dir_path: str) -> list[str]:
    """Safe os.listdir that filters known junk and returns [] on missing dirs."""
    if not os.path.isdir(dir_path):
        return []

    ignored_files = {".DS_Store", ".localized"}
    return [val for val in os.listdir(dir_path) if val not in ignored_files]


def _relative_path(path: str) -> str:
    if path.startswith("/"):
        return path[1:]
    return path


def pathjoin(path: str, *args: str) -> str:
    """Join paths treating every argument after the first as relative."""
    if args:
        normed_args = [_relative_path(arg) for arg in args]
        return os.path.join(path, *normed_args)
    return os.path.join(path)


def get_homedirs() -> list[HomeDir]:
    """Return HomeDir objects for accounts under ROOT_PATH/Users."""
    homedirs: list[HomeDir] = []
    users_dir_path = pathjoin(ROOT_PATH, "Users")
    for user_name in listdir(users_dir_path):
        if not user_name.startswith("."):
            homedirs.append(HomeDir(user_name, pathjoin(ROOT_PATH, "Users", user_name)))
    return homedirs


# Historical private name
_get_homedirs = get_homedirs
