"""System, SIP, Gatekeeper, network, process, and related collectors."""

from __future__ import annotations

import os
from typing import Any

import osxcollector.paths as paths_mod
from osxcollector import __version__
from osxcollector.collectors.base import CollectorBase, foreach_homedir
from osxcollector.fileinfo import get_file_info
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import pathjoin
from osxcollector.subprocess_utils import run_command

PATH_ENVIRONMENT_NAME = "PATH"


class SystemCollectors(CollectorBase):
    def _version_string(self) -> None:
        Logger.log_dict({"osxcollector_version": __version__})

    def _is_fde_enabled(self) -> bool:
        try:
            result = run_command(["fdesetup", "status"], timeout=15)
            return "On" in (result.stdout or "")
        except (OSError, TimeoutError):
            return False

    def _collect_system_info(self) -> None:
        sysname, nodename, release, version, machine = os.uname()
        record = {
            "sysname": sysname,
            "nodename": nodename,
            "release": release,
            "version": version,
            "machine": machine,
            "fde": self._is_fde_enabled(),
        }
        Logger.log_dict(record)

    def _collect_binary_names_in_path(self) -> None:
        exe_files: list[str] = []

        def is_exe(fpath: str) -> bool:
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        if PATH_ENVIRONMENT_NAME in os.environ:
            for bin_dir in os.environ[PATH_ENVIRONMENT_NAME].split(os.pathsep):
                for root_dir, _dirs, files in os.walk(bin_dir):
                    for the_file in files:
                        file_path = os.path.join(root_dir, the_file)
                        if is_exe(file_path):
                            exe_files.append(file_path)
        Logger.log_dict({"executable_files": exe_files})

    def _collect_full_hash(self) -> None:
        self._log_file_info_for_directory(paths_mod.ROOT_PATH)

    def _collect_kext(self) -> None:
        for kext_path in ("System/Library/Extensions", "Library/Extensions"):
            self._log_packages_in_dir(pathjoin(paths_mod.ROOT_PATH, kext_path))

    def _collect_system_extensions(self) -> None:
        for path in (
            "Library/SystemExtensions",
            "System/Library/SystemExtensions",
        ):
            self._log_packages_in_dir(pathjoin(paths_mod.ROOT_PATH, path))

    def _collect_sip(self) -> None:
        try:
            result = run_command(["csrutil", "status"], timeout=15)
            Logger.log_dict(
                {
                    "csrutil_status": (result.stdout or "").strip(),
                    "returncode": result.returncode,
                }
            )
        except (OSError, TimeoutError) as e:
            Logger.log_exception(e, message="sip")

    def _collect_gatekeeper(self) -> None:
        try:
            result = run_command(["spctl", "--status"], timeout=15)
            Logger.log_dict(
                {
                    "spctl_status": (result.stdout or result.stderr or "").strip(),
                    "returncode": result.returncode,
                }
            )
        except (OSError, TimeoutError) as e:
            Logger.log_exception(e, message="gatekeeper")

    def _collect_network(self) -> None:
        commands = [
            (["ifconfig", "-a"], "ifconfig"),
            (["networksetup", "-listallhardwareports"], "hardware_ports"),
            (["scutil", "--dns"], "dns"),
            (["netstat", "-anv"], "netstat"),
        ]
        for argv, label in commands:
            try:
                result = run_command(argv, timeout=30)
                Logger.log_dict(
                    {
                        "command": label,
                        "returncode": result.returncode,
                        "stdout": (result.stdout or "")[:200_000],
                        "stderr": (result.stderr or "")[:20_000],
                    }
                )
            except (OSError, TimeoutError) as e:
                Logger.log_exception(e, message=f"network:{label}")

    def _collect_processes(self) -> None:
        if paths_mod.ROOT_PATH != "/":
            Logger.log_warning("processes section skipped for offline root path")
            return
        try:
            result = run_command(["ps", "axo", "pid,ppid,user,uid,gid,command"], timeout=30)
            Logger.log_dict(
                {
                    "ps": (result.stdout or "")[:500_000],
                    "returncode": result.returncode,
                }
            )
        except (OSError, TimeoutError) as e:
            Logger.log_exception(e, message="processes")

    def _collect_codesign_sample(self) -> None:
        """Enrich a small set of PATH binaries with codesign metadata."""
        sample: list[str] = []
        path_env = os.environ.get(PATH_ENVIRONMENT_NAME, "")
        for bin_dir in path_env.split(os.pathsep)[:5]:
            if not os.path.isdir(bin_dir):
                continue
            for name in sorted(os.listdir(bin_dir))[:20]:
                full = os.path.join(bin_dir, name)
                if os.path.isfile(full) and os.access(full, os.X_OK):
                    sample.append(full)
        for file_path in sample[:50]:
            try:
                result = run_command(
                    ["codesign", "-dv", "--verbose=4", file_path],
                    timeout=10,
                )
                Logger.log_dict(
                    {
                        "file_path": file_path,
                        "codesign": (result.stderr or result.stdout or "")[:20_000],
                        "returncode": result.returncode,
                    }
                )
            except (OSError, TimeoutError) as e:
                Logger.log_exception(e, message=f"codesign:{file_path}")

    @foreach_homedir
    def _collect_shell_history(self, homedir: Any) -> None:
        history_files = [
            ".bash_history",
            ".zsh_history",
            ".python_history",
            ".local/share/fish/fish_history",
        ]
        for rel in history_files:
            path = pathjoin(homedir.path, rel)
            if os.path.isfile(path):
                info = get_file_info(path, True)
                info["history_file"] = rel
                Logger.log_dict(info)

    @foreach_homedir
    def _collect_ssh(self, homedir: Any) -> None:
        ssh_dir = pathjoin(homedir.path, ".ssh")
        if not os.path.isdir(ssh_dir):
            return
        for name in ("known_hosts", "authorized_keys", "config"):
            path = pathjoin(ssh_dir, name)
            if os.path.isfile(path):
                try:
                    with open(path, encoding="utf-8", errors="replace") as handle:
                        Logger.log_dict(
                            {
                                "file_path": path,
                                "contents": handle.read()[:200_000],
                            }
                        )
                except OSError as e:
                    Logger.log_exception(e, message=f"ssh:{path}")

    def _collect_tcc(self) -> None:
        tcc_paths = [
            pathjoin(paths_mod.ROOT_PATH, "Library/Application Support/com.apple.TCC/TCC.db"),
        ]
        for homedir in self.homedirs:
            tcc_paths.append(
                pathjoin(homedir.path, "Library/Application Support/com.apple.TCC/TCC.db"),
            )
        for db_path in tcc_paths:
            if os.path.isfile(db_path):
                with Logger.Extra("osxcollector_subsection", "tcc_db"):
                    self._log_sqlite_db(db_path)

    def _collect_evidence_metadata(self, *, incident_id: str, live: bool, argv: list[str]) -> None:
        sysname, nodename, release, version, machine = os.uname()
        Logger.log_dict(
            {
                "osxcollector_evidence_metadata": True,
                "collector_version": __version__,
                "incident_id": incident_id,
                "live_collection": live,
                "root_path": paths_mod.ROOT_PATH,
                "hostname": nodename,
                "uname": {
                    "sysname": sysname,
                    "release": release,
                    "version": version,
                    "machine": machine,
                },
                "argv": argv,
            }
        )
