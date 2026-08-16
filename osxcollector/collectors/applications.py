"""Accounts, applications, quarantines, downloads, and mail collectors."""

from __future__ import annotations

import os
from typing import Any

import osxcollector.paths as paths_mod
from osxcollector.collectors.base import CollectorBase, foreach_homedir
from osxcollector.dictutils import DictUtils
from osxcollector.fileinfo import get_file_info
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import listdir, pathjoin


class AccountCollectors(CollectorBase):
    def _collect_accounts(self) -> None:
        accounts = [
            ("system_admins", self._collect_accounts_system_admins),
            ("system_users", self._collect_accounts_system_users),
            ("social_accounts", self._collect_accounts_social_accounts),
            ("recent_items", self._collect_accounts_recent_items),
        ]
        for subsection_name, collector in accounts:
            with Logger.Extra("osxcollector_subsection", subsection_name):
                collector()

    def _collect_accounts_system_admins(self) -> None:
        sys_admin_plist_path = pathjoin(
            paths_mod.ROOT_PATH,
            "private/var/db/dslocal/nodes/Default/groups/admin.plist",
        )
        sys_admin_plist = self._read_plist(sys_admin_plist_path)
        for admin in sys_admin_plist.get("groupmembers", []):
            self.admins.append(admin)
        for admin in sys_admin_plist.get("users", []):
            self.admins.append(admin)
        Logger.log_dict({"admins": self.admins})

    def _collect_accounts_system_users(self) -> None:
        users_root = pathjoin(paths_mod.ROOT_PATH, "private/var/db/dslocal/nodes/Default/users")
        for user_name in listdir(users_root):
            if user_name.startswith("."):
                continue
            user_details: dict[str, Any] = {}
            sys_user_plist_path = pathjoin(users_root, user_name)
            sys_user_plist = self._read_plist(sys_user_plist_path)
            user_details["names"] = [
                {"name": val, "is_admin": (val in self.admins)} for val in sys_user_plist.get("name", [])
            ]
            user_details["realname"] = list(sys_user_plist.get("realname", []))
            user_details["shell"] = list(sys_user_plist.get("shell", []))
            user_details["home"] = list(sys_user_plist.get("home", []))
            user_details["uid"] = list(sys_user_plist.get("uid", []))
            user_details["gid"] = list(sys_user_plist.get("gid", []))
            user_details["generateduid"] = [
                {"name": val, "is_admin": (val in self.admins)} for val in sys_user_plist.get("generateduid", [])
            ]
            Logger.log_dict(user_details)

    @foreach_homedir
    def _collect_accounts_social_accounts(self, homedir: Any) -> None:
        for db_name in ("Accounts4.sqlite", "Accounts3.sqlite"):
            user_accounts_path = pathjoin(homedir.path, f"Library/Accounts/{db_name}")
            if os.path.isfile(user_accounts_path):
                self._log_sqlite_db(user_accounts_path)

    @foreach_homedir
    def _collect_accounts_recent_items(self, homedir: Any) -> None:
        recent_items_account_plist_path = pathjoin(
            homedir.path,
            "Library/Preferences/com.apple.recentitems.plist",
        )
        recents_plist = self._read_plist(recent_items_account_plist_path)
        recents = [
            ("server", "RecentServers"),
            ("document", "RecentDocuments"),
            ("application", "RecentApplications"),
            ("host", "Hosts"),
        ]
        for recent_type, recent_key in recents:
            with Logger.Extra("recent_type", recent_type):
                for recent in DictUtils.get_deep(recents_plist, f"{recent_key}.CustomListItems", []):
                    recent_details = {f"{recent_type}_name": recent["Name"]}
                    if recent_type == "host":
                        recent_details["host_url"] = recent["URL"]
                    Logger.log_dict(recent_details)


class ApplicationCollectors(CollectorBase):
    @foreach_homedir
    def _log_user_quarantines(self, homedir: Any) -> None:
        db_path = pathjoin(
            homedir.path,
            "Library/Preferences/com.apple.LaunchServices.QuarantineEventsV2",
        )
        if not os.path.isfile(db_path):
            db_path = pathjoin(
                homedir.path,
                "Library/Preferences/com.apple.LaunchServices.QuarantineEvents",
            )
        self._log_sqlite_db(db_path)

    def _log_xprotect(self) -> None:
        xprotect_files = [
            "System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/XProtect.plist",
            "System/Library/CoreServices/CoreTypes.bundle/Contents/Resources/XProtect.meta.plist",
            "Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Resources/XProtect.plist",
            "Library/Apple/System/Library/CoreServices/XProtect.bundle/Contents/Resources/XProtect.meta.plist",
        ]
        for file_path in xprotect_files:
            full = pathjoin(paths_mod.ROOT_PATH, file_path)
            if os.path.exists(full):
                Logger.log_dict(get_file_info(full))

    def _collect_quarantines(self) -> None:
        self._log_user_quarantines()
        self._log_xprotect()

    @foreach_homedir
    def _collect_downloads(self, homedir: Any) -> None:
        directories_to_hash = [
            ("downloads", "Downloads"),
            ("email_downloads", "Library/Mail Downloads"),
            ("old_email_downloads", "Library/Containers/com.apple.mail/Data/Library/Mail Downloads"),
        ]
        for subsection_name, path_to_dir in directories_to_hash:
            with Logger.Extra("osxcollector_subsection", subsection_name):
                self._log_file_info_for_directory(pathjoin(homedir.path, path_to_dir))

    @foreach_homedir
    def _collect_user_applications(self, homedir: Any) -> None:
        self._log_packages_in_dir(pathjoin(homedir.path, "Applications"))

    def _collect_applications(self) -> None:
        with Logger.Extra("osxcollector_subsection", "applications"):
            self._log_packages_in_dir(pathjoin(paths_mod.ROOT_PATH, "Applications"))
            self._collect_user_applications()
        with Logger.Extra("osxcollector_subsection", "install_history"):
            plist = self._read_plist(
                pathjoin(paths_mod.ROOT_PATH, "Library/Receipts/InstallHistory.plist"),
                default=[],
            )
            if isinstance(plist, list):
                for installed_app in plist:
                    Logger.log_dict(installed_app)

    @foreach_homedir
    def _collect_mail(self, homedir: Any) -> None:
        for mail_path in ("Library/Mail", "Library/Mail Downloads"):
            self._log_file_info_for_directory(pathjoin(homedir.path, mail_path))
