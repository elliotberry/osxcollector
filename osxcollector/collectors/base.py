"""Collector base helpers."""

from __future__ import annotations

import functools
import json
import os
from collections.abc import Callable
from typing import Any

from osxcollector.dictutils import DictUtils
from osxcollector.fileinfo import get_file_info
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import get_homedirs, listdir, pathjoin
from osxcollector.plist_utils import read_plist
from osxcollector.sqlite_utils import log_directories_of_dbs, log_sqlite_db, log_sqlite_dbs_for_subsections


def foreach_homedir(func: Callable[..., None]) -> Callable[..., None]:
    """Call a method once per user home directory, tagging username in logs."""

    @functools.wraps(func)
    def wrapper(self: Any, *args: Any, **kwargs: Any) -> None:
        for homedir in self.homedirs:
            with Logger.Extra("osxcollector_username", homedir.user_name):
                try:
                    func(self, *args, homedir=homedir, **kwargs)
                except (OSError, ValueError, TypeError) as e:
                    Logger.log_exception(e)

    return wrapper


class CollectorBase:
    """Shared helpers used by section collectors."""

    def __init__(self) -> None:
        self.admins: list[Any] = []
        self.homedirs = get_homedirs()
        self.firefox_ignored_sqlite_keys: dict[str, dict[str, list[str]]] = {}
        self.safari_ignored_sqlite_keys: dict[str, dict[str, list[str]]] = {}
        self.chrome_ignored_sqlite_keys: dict[str, dict[str, list[str]]] = {}

    def _read_plist(self, plist_path: str, default: Any = None) -> Any:
        return read_plist(plist_path, default=default)

    def _log_items_in_plist(self, plist: Any, path: str, transform: Callable | None = None) -> None:
        for item in DictUtils.get_deep(plist, path=path, default=[]):
            try:
                if transform:
                    item = transform(item)
                Logger.log_dict(item)
            except (OSError, TypeError, ValueError) as exc:
                Logger.log_exception(exc)

    def _log_file_info_for_directory(self, dir_path: str, recurse: bool = True) -> None:
        """Log file info for every file under dir_path (always recursive, matching v1)."""
        del recurse  # historical signature; always walk fully
        if not os.path.isdir(dir_path):
            Logger.log_warning(f"Directory not found {dir_path}")
            return

        from concurrent.futures import ThreadPoolExecutor

        file_paths = [
            pathjoin(root, file_name) for root, _dirs, file_names in os.walk(dir_path) for file_name in file_names
        ]

        def _one(path: str) -> None:
            try:
                Logger.log_dict(get_file_info(path, True))
            except OSError as exc:
                Logger.log_exception(exc)

        workers = min(8, max(1, (os.cpu_count() or 2)))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            list(pool.map(_one, file_paths))

    def _should_walk(self, sub_dir_path: str) -> bool:
        return any(
            sub_dir_path.endswith(extension) for extension in (".app", ".kext", ".osax", "Contents", ".systemextension")
        )

    def _log_packages_in_dir(self, dir_path: str) -> None:
        plist_file = "Info.plist"
        walk = (
            (sub_dir_path, file_names)
            for sub_dir_path, _, file_names in os.walk(dir_path)
            if self._should_walk(sub_dir_path) and plist_file in file_names
        )
        for sub_dir_path, _file_names in walk:
            cfbundle_executable_path = "MacOS" if sub_dir_path.endswith("Contents") else ""
            plist_path = pathjoin(sub_dir_path, plist_file)
            plist = self._read_plist(plist_path)
            cfbundle_executable = plist.get("CFBundleExecutable") if isinstance(plist, dict) else None
            if cfbundle_executable:
                file_path = pathjoin(sub_dir_path, cfbundle_executable_path, cfbundle_executable)
                file_info = get_file_info(file_path)
                file_info["osxcollector_plist_path"] = plist_path
                file_info["osxcollector_bundle_id"] = plist.get("CFBundleIdentifier", "")
                Logger.log_dict(file_info)

    def _log_json_file(self, dir_path: str, file_name: str) -> None:
        try:
            with open(pathjoin(dir_path, file_name), encoding="utf-8") as fp:
                record = json.loads(fp.read())
                with Logger.Extra("osxcollector_json_file", file_name):
                    Logger.log_dict({"contents": record})
        except (OSError, json.JSONDecodeError, UnicodeDecodeError) as log_json_e:
            Logger.log_exception(
                log_json_e,
                message=f"failed _log_json_file dir_path[{dir_path}] file_name[{file_name}]",
            )

    def _collect_json_files(self, dir_path: str) -> None:
        if not os.path.isdir(dir_path):
            Logger.log_warning(f"Directory not found {dir_path}")
            return
        for file_name in listdir(dir_path):
            if file_name.endswith(".json"):
                self._log_json_file(dir_path, file_name)

    def _log_sqlite_db(self, sqlite_db_path: str, ignore: dict | None = None) -> None:
        log_sqlite_db(sqlite_db_path, ignore)

    def _log_sqlite_dbs_for_subsections(self, *args: Any, **kwargs: Any) -> None:
        log_sqlite_dbs_for_subsections(*args, **kwargs)

    def _log_directories_of_dbs(self, *args: Any, **kwargs: Any) -> None:
        log_directories_of_dbs(*args, **kwargs)
