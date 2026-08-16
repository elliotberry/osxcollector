"""Startup, login items, and background persistence collectors."""

from __future__ import annotations

import os
from typing import Any

import osxcollector.paths as paths_mod
from osxcollector.collectors.base import CollectorBase, foreach_homedir
from osxcollector.fileinfo import get_file_info
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import listdir, pathjoin


class StartupCollectors(CollectorBase):
    def _log_startup_items(self, dir_path: str) -> None:
        if not os.path.isdir(dir_path):
            Logger.log_warning(f"Directory not found {dir_path}")
            return

        for entry in listdir(dir_path):
            plist_path = pathjoin(dir_path, entry, "StartupParameters.plist")
            plist = self._read_plist(plist_path)
            try:
                self._log_items_in_plist(
                    plist,
                    "Provides",
                    transform=lambda x, _entry=entry: get_file_info(pathjoin(dir_path, _entry, x)),
                )
            except (OSError, TypeError, ValueError) as log_startup_items_e:
                Logger.log_exception(log_startup_items_e)

    def _log_launch_agents(self, dir_path: str) -> None:
        if not os.path.isdir(dir_path):
            Logger.log_warning(f"Directory not found {dir_path}")
            return

        for entry in listdir(dir_path):
            plist_path = pathjoin(dir_path, entry)
            plist = self._read_plist(plist_path)
            if not isinstance(plist, dict):
                continue
            try:
                program = plist.get("Program", "")
                program_with_arguments = plist.get("ProgramArguments", [])
                if program or len(program_with_arguments):
                    file_path = pathjoin(paths_mod.ROOT_PATH, program or program_with_arguments[0])
                    file_info = get_file_info(file_path)
                    file_info["label"] = plist.get("Label")
                    file_info["program"] = file_path
                    file_info["osxcollector_plist"] = plist_path
                    if len(program_with_arguments) > 1:
                        file_info["arguments"] = list(program_with_arguments)[1:]
                    Logger.log_dict(file_info)
            except (OSError, TypeError, ValueError, IndexError) as log_launch_agents_e:
                Logger.log_exception(log_launch_agents_e)

    @foreach_homedir
    def _log_user_launch_agents(self, homedir: Any) -> None:
        self._log_launch_agents(pathjoin(homedir.path, "Library/LaunchAgents/"))

    @foreach_homedir
    def _log_user_login_items(self, homedir: Any) -> None:
        plist_path = pathjoin(homedir.path, "Library/Preferences/com.apple.loginitems.plist")
        plist = self._read_plist(plist_path)
        self._log_items_in_plist(plist, "SessionItems.CustomListItems")

    @foreach_homedir
    def _log_background_items(self, homedir: Any) -> None:
        """Best-effort Background Task Management / modern login item artifacts."""
        candidates = [
            "Library/Application Support/com.apple.backgroundtaskmanagementagent/backgrounditems.btm",
            "Library/Application Support/com.apple.backgroundtaskmanagementagent",
            "Library/Preferences/com.apple.loginwindow.plist",
        ]
        for rel in candidates:
            path = pathjoin(homedir.path, rel)
            if os.path.isfile(path):
                Logger.log_dict(get_file_info(path, True))
            elif os.path.isdir(path):
                self._log_file_info_for_directory(path)

    def _collect_startup(self) -> None:
        launch_agents = [
            "System/Library/LaunchAgents",
            "System/Library/LaunchDaemons",
            "Library/LaunchAgents",
            "Library/LaunchDaemons",
        ]
        with Logger.Extra("osxcollector_subsection", "launch_agents"):
            for dir_path in launch_agents:
                self._log_launch_agents(pathjoin(paths_mod.ROOT_PATH, dir_path))
            self._log_user_launch_agents()

        packages = [
            "System/Library/ScriptingAdditions",
            "Library/ScriptingAdditions",
        ]
        with Logger.Extra("osxcollector_subsection", "scripting_additions"):
            for dir_path in packages:
                self._log_packages_in_dir(pathjoin(paths_mod.ROOT_PATH, dir_path))

        startup_items = [
            "System/Library/StartupItems",
            "Library/StartupItems",
        ]
        with Logger.Extra("osxcollector_subsection", "startup_items"):
            for dir_path in startup_items:
                self._log_startup_items(pathjoin(paths_mod.ROOT_PATH, dir_path))

        with Logger.Extra("osxcollector_subsection", "login_items"):
            self._log_user_login_items()

        with Logger.Extra("osxcollector_subsection", "background_items"):
            self._log_background_items()

    def _collect_background_items(self) -> None:
        self._log_background_items()
