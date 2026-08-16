"""Archive system logs and compress collection output."""

from __future__ import annotations

import hashlib
import os
import shutil
from pathlib import Path

import osxcollector.paths as paths_mod
from osxcollector.debug import debugbreak
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import listdir, pathjoin
from osxcollector.subprocess_utils import run_command


class LogFileArchiver:
    def archive_logs(self, target_dir_path: str) -> None:
        to_archive = [
            ("private/var/log", "system.", None),
            ("Library/Logs", None, None),
            ("Library/Logs/DiagnosticReports", None, ".crash"),
            ("Library/Logs/DiagnosticReports", None, ".ips"),
        ]

        for log_path, log_file_prefix, log_file_suffix in to_archive:
            log_dir_path = pathjoin(paths_mod.ROOT_PATH, log_path)
            for file_name in listdir(log_dir_path):
                if log_file_prefix and not file_name.startswith(log_file_prefix):
                    continue
                if log_file_suffix and not file_name.endswith(log_file_suffix):
                    continue
                src = pathjoin(log_dir_path, file_name)
                if not os.path.isfile(src):
                    continue
                dst = pathjoin(target_dir_path, file_name)
                try:
                    shutil.copyfile(src, dst)
                except OSError as archive_e:
                    debugbreak()
                    Logger.log_exception(archive_e, message=f"src[{src}] dst[{dst}]")

    def archive_unified_logs(
        self,
        target_dir_path: str,
        *,
        last: str = "1h",
        timeout: float = 120.0,
    ) -> None:
        """Export a window of unified logs via `log show` when available (live root)."""
        if paths_mod.ROOT_PATH != "/":
            return
        out_path = pathjoin(target_dir_path, "unified_log.json")
        try:
            result = run_command(
                ["log", "show", "--style", "json", "--last", last],
                timeout=timeout,
                text=True,
            )
            if result.returncode == 0 and result.stdout:
                stdout = result.stdout if isinstance(result.stdout, str) else result.stdout.decode("utf-8", "replace")
                Path(out_path).write_text(stdout, encoding="utf-8")
            elif result.stderr:
                stderr = result.stderr if isinstance(result.stderr, str) else result.stderr.decode("utf-8", "replace")
                Logger.log_warning(f"unified log export failed: {stderr.strip()}")
        except (OSError, TimeoutError) as e:
            Logger.log_exception(e, message="archive_unified_logs")

    def compress_directory(self, file_name: str, output_dir_path: str, target_dir_path: str) -> str | None:
        try:
            archive_path = shutil.make_archive(
                file_name,
                format="gztar",
                root_dir=output_dir_path,
                base_dir=target_dir_path,
            )
            return archive_path
        except OSError as compress_directory_e:
            debugbreak()
            Logger.log_exception(compress_directory_e)
            return None


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_sha256_sidecar(archive_path: str) -> str:
    digest = sha256_file(archive_path)
    sidecar = f"{archive_path}.sha256"
    Path(sidecar).write_text(f"{digest}  {os.path.basename(archive_path)}\n", encoding="utf-8")
    return digest
