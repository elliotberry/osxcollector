"""Main Collector composing all section collectors."""

from __future__ import annotations

import time
from collections.abc import Callable

from osxcollector.collectors.applications import AccountCollectors, ApplicationCollectors
from osxcollector.collectors.browsers import BrowserCollectors
from osxcollector.collectors.startup import StartupCollectors
from osxcollector.collectors.system import SystemCollectors
from osxcollector.console import Console
from osxcollector.debug import debugbreak
from osxcollector.logging_jsonl import Logger


class Collector(
    SystemCollectors,
    StartupCollectors,
    BrowserCollectors,
    ApplicationCollectors,
    AccountCollectors,
):
    """Examines plists, sqlite DBs, and hashes files for malware analysis."""

    SECTION_METHODS: list[tuple[str, str]] = [
        ("version", "_version_string"),
        ("system_info", "_collect_system_info"),
        ("kext", "_collect_kext"),
        ("system_extensions", "_collect_system_extensions"),
        ("startup", "_collect_startup"),
        ("background_items", "_collect_background_items"),
        ("applications", "_collect_applications"),
        ("quarantines", "_collect_quarantines"),
        ("downloads", "_collect_downloads"),
        ("chrome", "_collect_chrome"),
        ("edge", "_collect_edge"),
        ("brave", "_collect_brave"),
        ("firefox", "_collect_firefox"),
        ("safari", "_collect_safari"),
        ("accounts", "_collect_accounts"),
        ("mail", "_collect_mail"),
        ("tcc", "_collect_tcc"),
        ("network", "_collect_network"),
        ("shell_history", "_collect_shell_history"),
        ("ssh", "_collect_ssh"),
        ("processes", "_collect_processes"),
        ("sip", "_collect_sip"),
        ("gatekeeper", "_collect_gatekeeper"),
        ("codesign", "_collect_codesign_sample"),
        ("executables", "_collect_binary_names_in_path"),
        ("full_hash", "_collect_full_hash"),
    ]

    DEFAULT_SKIP = {"full_hash", "codesign"}

    def collect(self, section_list: list[str] | None = None) -> None:
        sections: list[tuple[str, Callable[[], None]]] = [
            (name, getattr(self, method_name)) for name, method_name in self.SECTION_METHODS
        ]
        wanted = self.sections_to_run(section_list)
        to_run = [(name, method) for name, method in sections if name in wanted]
        total = len(to_run)

        for index, (section_name, collection_method) in enumerate(to_run, start=1):
            with Logger.Extra("osxcollector_section", section_name):
                started = time.perf_counter()
                before = Logger.lines_written
                Console.section_start(index, total, section_name)
                try:
                    collection_method()
                except Exception as section_e:
                    debugbreak()
                    Logger.log_exception(section_e, message="failed section")
                finally:
                    Console.section_end(Logger.lines_written - before, time.perf_counter() - started)

    @classmethod
    def list_sections(cls) -> list[str]:
        return [name for name, _ in cls.SECTION_METHODS]

    @classmethod
    def sections_to_run(cls, section_list: list[str] | None = None) -> list[str]:
        """Return section names that will run, preserving SECTION_METHODS order."""
        names = [name for name, _ in cls.SECTION_METHODS]
        if not section_list:
            return [name for name in names if name not in cls.DEFAULT_SKIP]
        selected = set(section_list)
        return [name for name in names if name in selected]

    @classmethod
    def default_skipped_sections(cls, section_list: list[str] | None = None) -> list[str]:
        """Names skipped by default when the caller did not pass an explicit list."""
        if section_list:
            return []
        return [name for name, _ in cls.SECTION_METHODS if name in cls.DEFAULT_SKIP]
