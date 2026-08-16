"""SQLite dumping helpers with safer temp copies and identifier checks."""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import tempfile
from collections.abc import Callable
from pathlib import Path

from osxcollector.logging_jsonl import Logger
from osxcollector.normalize import normalize_val
from osxcollector.paths import listdir, pathjoin

# Patchable alias (tests historically mock connect)
connect = sqlite3.connect

_SAFE_IDENT = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _quote_ident(name: str) -> str:
    if not _SAFE_IDENT.match(name):
        raise ValueError(f"unsafe sqlite identifier: {name!r}")
    return f'"{name}"'


def _connect_readonly(db_path: str) -> sqlite3.Connection:
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def log_sqlite_table(
    table_name: str,
    cursor: sqlite3.Cursor,
    ignore_keys: list[str] | None,
) -> None:
    ignore_keys = ignore_keys or []
    with Logger.Extra("osxcollector_table_name", table_name):
        try:
            cursor.execute(f"SELECT * from {_quote_ident(table_name)}")
            rows = cursor.fetchall()
            if not rows:
                return
            column_names = [description[0].lower() for description in cursor.description]
            for row in rows:
                record = {}
                for index, column_name in enumerate(column_names):
                    if column_name not in ignore_keys:
                        try:
                            record[column_name] = normalize_val(row[index], column_name)
                        except Exception as per_row_e:
                            Logger.log_exception(
                                per_row_e,
                                message=f"failed normalizing {column_name}",
                            )
                Logger.log_dict(record)
        except (sqlite3.Error, ValueError, OSError) as per_table_e:
            Logger.log_exception(per_table_e, message="failed log_sqlite_table")


def raw_log_sqlite_db(sqlite_db_path: str, ignore: dict[str, list[str]] | None) -> None:
    ignore = ignore or {}
    with connect(sqlite_db_path) as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT * from sqlite_master WHERE type = "table"')
        tables = cursor.fetchall()
        for table in tables:
            table_name = table[2]
            if not _SAFE_IDENT.match(table_name):
                Logger.log_warning(f"Skipping unsafe sqlite table name {table_name!r}")
                continue
            ignore_keys = ignore.get(table_name, [])
            log_sqlite_table(table_name, cursor, ignore_keys)


def log_sqlite_db(sqlite_db_path: str, ignore: dict[str, list[str]] | None = None) -> None:
    """Dump tables from a SQLite database into JSONL records."""
    if ignore is None:
        ignore = {}

    if not os.path.isfile(sqlite_db_path):
        Logger.log_warning(f"File not found {sqlite_db_path}")
        return

    with Logger.Extra("osxcollector_db_path", sqlite_db_path):
        try:
            try:
                with _connect_readonly(sqlite_db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('SELECT * from sqlite_master WHERE type = "table"')
                    tables = cursor.fetchall()
                    for table in tables:
                        table_name = table[2]
                        if not _SAFE_IDENT.match(table_name):
                            Logger.log_warning(f"Skipping unsafe sqlite table name {table_name!r}")
                            continue
                        ignore_keys = ignore.get(table_name, [])
                        log_sqlite_table(table_name, cursor, ignore_keys)
                return
            except sqlite3.Error:
                pass

            raw_log_sqlite_db(sqlite_db_path, ignore)
        except sqlite3.Error as connection_e:
            message = str(connection_e).lower()
            if "locked" in message:
                with tempfile.TemporaryDirectory(prefix="osxcollector_sqlite_") as tmpdir:
                    tmp_path = os.path.join(tmpdir, os.path.basename(sqlite_db_path))
                    shutil.copyfile(sqlite_db_path, tmp_path)
                    # Also copy WAL/SHM if present for a consistent snapshot
                    for suffix in ("-wal", "-shm"):
                        side = f"{sqlite_db_path}{suffix}"
                        if os.path.isfile(side):
                            shutil.copyfile(side, f"{tmp_path}{suffix}")
                    raw_log_sqlite_db(tmp_path, ignore)
                Logger.log_warning(f"{sqlite_db_path} was locked. Copied to tempfile & analyzed.")
            else:
                Logger.log_exception(connection_e, message="failed log_sqlite_db")


def log_sqlite_dbs_for_subsections(
    sqlite_dbs: list[tuple[str, str]],
    profile_path: str,
    ignored_sqlite_keys: dict[str, dict[str, list[str]]] | None = None,
) -> None:
    ignored_sqlite_keys = ignored_sqlite_keys or {}
    for subsection_name, db_name in sqlite_dbs:
        with Logger.Extra("osxcollector_subsection", subsection_name):
            ignore = ignored_sqlite_keys.get(subsection_name, {})
            sqlite_db_path = pathjoin(profile_path, db_name)
            log_sqlite_db(sqlite_db_path, ignore)


def log_directories_of_dbs(
    directories_of_dbs: list[tuple[str, str]],
    profile_path: str,
    ignored_sqlite_keys: dict[str, dict[str, list[str]]] | None = None,
    ignore_db_path: Callable[[str], bool] | None = None,
) -> None:
    ignored_sqlite_keys = ignored_sqlite_keys or {}
    if ignore_db_path is None:

        def ignore_db_path(sqlite_db_path: str) -> bool:
            return False

    for subsection_name, dir_name in directories_of_dbs:
        dir_path = pathjoin(profile_path, dir_name)
        if not os.path.isdir(dir_path):
            continue
        with Logger.Extra("osxcollector_subsection", subsection_name):
            ignore = ignored_sqlite_keys.get(subsection_name, {})
            for file_name in listdir(dir_path):
                sqlite_db_path = pathjoin(dir_path, file_name)
                if ignore_db_path(sqlite_db_path):
                    continue
                log_sqlite_db(sqlite_db_path, ignore)
