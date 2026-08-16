"""Browser collectors (Chrome family, Firefox, Safari)."""

from __future__ import annotations

import os
from typing import Any

from osxcollector.collectors.base import CollectorBase, foreach_homedir
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import pathjoin


class BrowserCollectors(CollectorBase):
    @foreach_homedir
    def _collect_firefox(self, homedir: Any) -> None:
        all_profiles_path = pathjoin(homedir.path, "Library/Application Support/Firefox/Profiles")
        if not os.path.isdir(all_profiles_path):
            Logger.log_warning(f"Directory not found {all_profiles_path}")
            return

        from osxcollector.paths import listdir

        for profile_name in listdir(all_profiles_path):
            profile_path = pathjoin(all_profiles_path, profile_name)
            sqlite_dbs = [
                ("cookies", "cookies.sqlite"),
                ("downloads", "downloads.sqlite"),
                ("formhistory", "formhistory.sqlite"),
                ("history", "places.sqlite"),
                ("permissions", "permissions.sqlite"),
                ("content_prefs", "content-prefs.sqlite"),
                ("webapps_store", "webappsstore.sqlite"),
                # Legacy / best-effort
                ("signons", "signons.sqlite"),
                ("addons", "addons.sqlite"),
                ("extension", "extensions.sqlite"),
                ("health_report", "healthreport.sqlite"),
            ]
            self._log_sqlite_dbs_for_subsections(
                sqlite_dbs,
                profile_path,
                self.firefox_ignored_sqlite_keys,
            )
            with Logger.Extra("osxcollector_subsection", "json_files"):
                self._collect_json_files(profile_path)
            for json_name in ("extensions.json", "handlers.json", "logins.json"):
                if os.path.isfile(pathjoin(profile_path, json_name)):
                    with Logger.Extra("osxcollector_subsection", "json_files"):
                        self._log_json_file(profile_path, json_name)

    @foreach_homedir
    def _collect_safari(self, homedir: Any) -> None:
        profile_path = pathjoin(homedir.path, "Library/Safari")
        if not os.path.isdir(profile_path):
            Logger.log_warning(f"Directory not found {profile_path}")
            return

        plists = [
            ("downloads", "Downloads.plist", "DownloadHistory"),
            ("history", "History.plist", "WebHistoryDates"),
            ("extensions", "Extensions/Extensions.plist", "Installed Extensions"),
        ]
        for subsection_name, plist_name, key_to_log in plists:
            with Logger.Extra("osxcollector_subsection", subsection_name):
                plist_path = pathjoin(profile_path, plist_name)
                plist = self._read_plist(plist_path)
                self._log_items_in_plist(plist, key_to_log)

        self._log_sqlite_dbs_for_subsections([("history", "History.db")], profile_path)

        directories_of_dbs = [
            ("databases", "Databases"),
            ("localstorage", "LocalStorage"),
        ]
        self._log_directories_of_dbs(
            directories_of_dbs,
            profile_path,
            self.safari_ignored_sqlite_keys,
        )

        with Logger.Extra("osxcollector_subsection", "extension_files"):
            self._log_file_info_for_directory(pathjoin(profile_path, "Extensions"))

    def _collect_chromium_family(self, homedir: Any, browser_name: str, support_rel: str) -> None:
        chrome_path = pathjoin(homedir.path, support_rel)
        if not os.path.isdir(chrome_path):
            Logger.log_warning(f"Directory not found {chrome_path}")
            return

        profile_paths = [
            pathjoin(chrome_path, subdir)
            for subdir in os.listdir(chrome_path)
            if os.path.isdir(os.path.join(chrome_path, subdir)) and os.path.isfile(f"{chrome_path}/{subdir}/History")
        ]

        sqlite_dbs = [
            ("history", "History"),
            ("archived_history", "Archived History"),
            ("cookies", "Cookies"),
            ("login_data", "Login Data"),
            ("top_sites", "Top Sites"),
            ("web_data", "Web Data"),
        ]
        directories_of_dbs = [
            ("databases", "databases"),
            ("local_storage", "Local Storage"),
        ]

        def ignore_db_path(sqlite_db_path: str) -> bool:
            return sqlite_db_path.endswith("-journal") or os.path.isdir(sqlite_db_path)

        for profile_path in profile_paths:
            with Logger.Extra("browser", browser_name):
                self._log_directories_of_dbs(
                    directories_of_dbs,
                    profile_path,
                    self.chrome_ignored_sqlite_keys,
                    ignore_db_path,
                )
                self._log_sqlite_dbs_for_subsections(
                    sqlite_dbs,
                    profile_path,
                    self.chrome_ignored_sqlite_keys,
                )
                with Logger.Extra("osxcollector_subsection", "preferences"):
                    self._log_json_file(profile_path, "Preferences")
                    if os.path.isfile(pathjoin(profile_path, "preferences")):
                        self._log_json_file(profile_path, "preferences")

    @foreach_homedir
    def _collect_chrome(self, homedir: Any) -> None:
        self._collect_chromium_family(
            homedir,
            "chrome",
            "Library/Application Support/Google/Chrome",
        )

    @foreach_homedir
    def _collect_edge(self, homedir: Any) -> None:
        self._collect_chromium_family(
            homedir,
            "edge",
            "Library/Application Support/Microsoft Edge",
        )

    @foreach_homedir
    def _collect_brave(self, homedir: Any) -> None:
        self._collect_chromium_family(
            homedir,
            "brave",
            "Library/Application Support/BraveSoftware/Brave-Browser",
        )
