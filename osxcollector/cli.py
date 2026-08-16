"""Command-line entry point for OSXCollector."""

from __future__ import annotations

import os
import shutil
import sys
from argparse import ArgumentParser
from datetime import UTC, datetime

import osxcollector.debug as debug_mod
import osxcollector.paths as paths_mod
from osxcollector import __version__
from osxcollector.archive import LogFileArchiver, write_sha256_sidecar
from osxcollector.collectors.collector import Collector
from osxcollector.logging_jsonl import Logger
from osxcollector.paths import pathjoin


def build_parser() -> ArgumentParser:
    parser = ArgumentParser(description="OSXCollector forensic evidence collector for macOS")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    parser.add_argument(
        "-i",
        "--id",
        dest="incident_prefix",
        default="osxcollect",
        help="Identifier used as a prefix of the output file name.",
    )
    parser.add_argument(
        "-p",
        "--path",
        dest="rootpath",
        default="/",
        help="Path to the macOS system to audit (e.g. /mnt/xxx). Default: live system.",
    )
    parser.add_argument(
        "-s",
        "--section",
        dest="section_list",
        default=[],
        action="append",
        help="Run only the named section. May be specified more than once.",
    )
    parser.add_argument(
        "-d",
        "--debug",
        action="store_true",
        default=False,
        help="Enable verbose output and python breakpoints.",
    )
    parser.add_argument(
        "-c",
        "--collect-cookies",
        dest="collect_cookies_value",
        default=False,
        action="store_true",
        help="Collect cookies' value (may contain secrets).",
    )
    parser.add_argument(
        "-l",
        "--collect-local-storage",
        dest="collect_local_storage_value",
        default=False,
        action="store_true",
        help="Collect web browsers' local storage values (may contain secrets).",
    )
    parser.add_argument(
        "--list-sections",
        action="store_true",
        help="Print available collection sections and exit.",
    )
    parser.add_argument(
        "--outdir",
        dest="outdir",
        default=".",
        help="Directory where the incident folder / archive will be written.",
    )
    parser.add_argument(
        "--no-archive",
        action="store_true",
        help="Leave the incident directory in place; do not create a .tar.gz.",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=120.0,
        help="Timeout seconds for unified log export and similar commands.",
    )
    parser.add_argument(
        "--unified-log-last",
        default="1h",
        help="Window passed to `log show --last` when archiving unified logs.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.list_sections:
        for name in Collector.list_sections():
            print(name)
        return 0

    debug_mod.DEBUG_MODE = args.debug
    paths_mod.ROOT_PATH = args.rootpath

    euid = os.geteuid()
    egid = os.getegid()
    if paths_mod.ROOT_PATH == "/" and (euid != 0 and egid != 0):
        Logger.log_error("Must run as root!\n")
        return 1

    collector = Collector()

    if not args.collect_cookies_value:
        collector.firefox_ignored_sqlite_keys["cookies"] = {"moz_cookies": ["value"]}
        collector.chrome_ignored_sqlite_keys["cookies"] = {"cookies": ["value"]}

    if not args.collect_local_storage_value:
        collector.safari_ignored_sqlite_keys["localstorage"] = {"ItemTable": ["value"]}
        collector.chrome_ignored_sqlite_keys["local_storage"] = {"ItemTable": ["value"]}

    started = datetime.now(UTC)
    prefix = args.incident_prefix
    incident_id = f"{prefix}-{started.strftime('%Y_%m_%d-%H_%M_%S')}"

    output_directory = os.path.join(args.outdir, incident_id)
    os.makedirs(output_directory, exist_ok=True)
    output_file_name = pathjoin(output_directory, f"{incident_id}.json")

    archive_path = None
    with open(output_file_name, "w", encoding="utf-8") as output_file:
        Logger.set_output_file(output_file)
        with Logger.Extra("osxcollector_incident_id", incident_id):
            with Logger.Extra("osxcollector_section", "evidence_metadata"):
                collector._collect_evidence_metadata(
                    incident_id=incident_id,
                    live=(paths_mod.ROOT_PATH == "/"),
                    argv=["osxcollector", *argv],
                )
            collector.collect(section_list=args.section_list or None)

        log_file_archiver = LogFileArchiver()
        log_file_archiver.archive_logs(output_directory)
        try:
            log_file_archiver.archive_unified_logs(
                output_directory,
                last=args.unified_log_last,
                timeout=args.timeout,
            )
        except Exception as e:
            Logger.log_exception(e, message="unified_logs")

        if not args.no_archive:
            archive_path = log_file_archiver.compress_directory(
                os.path.join(args.outdir, incident_id),
                args.outdir,
                incident_id,
            )
            if archive_path and not args.debug:
                try:
                    shutil.rmtree(output_directory)
                except OSError as e:
                    Logger.log_exception(e)

    ended = datetime.now(UTC)
    if archive_path and os.path.isfile(archive_path):
        digest = write_sha256_sidecar(archive_path)
        sys.stderr.write(
            f"Wrote {Logger.lines_written} lines.\n"
            f"Output in {os.path.basename(archive_path)}\n"
            f"SHA-256 {digest}\n"
            f"Duration {(ended - started).total_seconds():.1f}s\n",
        )
    else:
        sys.stderr.write(
            f"Wrote {Logger.lines_written} lines.\n"
            f"Output in {output_directory}\n"
            f"Duration {(ended - started).total_seconds():.1f}s\n",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
