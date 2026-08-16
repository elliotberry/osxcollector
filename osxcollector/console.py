"""Operator-facing stderr output, separate from forensic JSONL records."""

from __future__ import annotations

import os
import sys
import threading
import traceback
from json import dumps
from typing import Any, TextIO

DIM = "\033[2m"
BOLD = "\033[1m"
YELLOW = "\033[33m"
RED = "\033[31m"
RESET = "\033[0m"

_SKIP_CONTEXT_KEYS = {"osxcollector_incident_id"}
_NAME_WIDTH = 20


def color_enabled_for(stream: TextIO) -> bool:
    """Return True when ANSI color is appropriate for stream."""
    if os.environ.get("NO_COLOR"):
        return False
    if os.environ.get("TERM") == "dumb":
        return False
    return hasattr(stream, "isatty") and stream.isatty()


def format_context(extras: dict[str, Any] | None) -> str:
    """Format Logger.Extra keys as k=v pairs, omitting the incident id."""
    if not extras:
        return ""
    parts = [f"{key}={val}" for key, val in extras.items() if key not in _SKIP_CONTEXT_KEYS]
    return " ".join(parts)


def _plural(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return singular
    return plural if plural is not None else f"{singular}s"


class Console:
    """Write progress, warnings, and errors to stderr."""

    stream: TextIO = sys.stderr
    debug = False
    warnings = 0
    errors = 0
    _color = False
    _lock = threading.Lock()
    _open_line = False
    _in_section = False
    _section_interrupted = False
    _section_prefix_len = 0

    @classmethod
    def reset(cls) -> None:
        """Clear counters and restore the default stream (for a new run / tests)."""
        cls.stream = sys.stderr
        cls.debug = False
        cls.warnings = 0
        cls.errors = 0
        cls._open_line = False
        cls._in_section = False
        cls._section_interrupted = False
        cls._section_prefix_len = 0
        cls._color = color_enabled_for(cls.stream)

    @classmethod
    def configure(cls, *, debug: bool | None = None, stream: TextIO | None = None) -> None:
        if stream is not None:
            cls.stream = stream
        if debug is not None:
            cls.debug = debug
        cls._color = color_enabled_for(cls.stream)

    @classmethod
    def _style(cls, code: str, text: str) -> str:
        if not cls._color:
            return text
        return f"{code}{text}{RESET}"

    @classmethod
    def _write(cls, text: str) -> None:
        cls.stream.write(text)
        cls.stream.flush()

    @classmethod
    def _break_open_line(cls) -> None:
        if cls._open_line:
            cls._write("\n")
            cls._open_line = False
            cls._section_interrupted = True

    @classmethod
    def banner(
        cls,
        *,
        version: str,
        incident_id: str,
        root: str,
        output: str,
        section_count: int,
        skipped: list[str] | None = None,
    ) -> None:
        skipped = skipped or []
        sections_line = f"  sections   {section_count}"
        if skipped:
            sections_line += f"  (skipping {', '.join(skipped)})"
        with cls._lock:
            cls._break_open_line()
            cls._write(cls._style(BOLD, f"OSXCollector {version}") + "\n")
            cls._write(cls._style(DIM, f"  incident   {incident_id}") + "\n")
            cls._write(cls._style(DIM, f"  root       {root}") + "\n")
            cls._write(cls._style(DIM, f"  output     {output}") + "\n")
            cls._write(cls._style(DIM, sections_line) + "\n")
            cls._write("\n")

    @classmethod
    def section_start(cls, index: int, total: int, name: str) -> None:
        prefix = f"  [{index:2d}/{total}] "
        line = prefix + f"{name:<{_NAME_WIDTH}}"
        with cls._lock:
            cls._break_open_line()
            cls._in_section = True
            cls._section_interrupted = False
            cls._section_prefix_len = len(prefix)
            cls._write(cls._style(DIM, line))
            cls._open_line = True

    @classmethod
    def section_end(cls, records: int, elapsed: float) -> None:
        unit = _plural(records, "record")
        stats = f"{records:>5d} {unit:<7} {elapsed:5.1f}s"
        with cls._lock:
            if cls._open_line and not cls._section_interrupted:
                cls._write(cls._style(DIM, f"  {stats}") + "\n")
                cls._open_line = False
            else:
                cls._break_open_line()
                pad = " " * (cls._section_prefix_len + _NAME_WIDTH)
                cls._write(cls._style(DIM, f"{pad}  {stats}") + "\n")
            cls._in_section = False
            cls._section_interrupted = False

    @classmethod
    def phase(cls, label: str, tag: str = "post") -> None:
        with cls._lock:
            cls._break_open_line()
            cls._write(cls._style(DIM, f"  [{tag}]  {label}") + "\n")

    @classmethod
    def warn(cls, message: str, context: str = "") -> None:
        extra = f"  {context}" if context and cls.debug else ""
        with cls._lock:
            cls.warnings += 1
            if cls._in_section:
                cls._break_open_line()
                body = f"          warn  {message}{extra}"
                cls._write(cls._style(YELLOW, body) + "\n")
            else:
                cls._break_open_line()
                body = f"  [WARN]  {message}{extra}"
                cls._write(cls._style(YELLOW, body) + "\n")

    @classmethod
    def error(cls, message: str, context: str = "") -> None:
        with cls._lock:
            cls.errors += 1
            cls._break_open_line()
            cls._write(cls._style(RED, f"  [ERROR] {message}") + "\n")
            if context:
                cls._write(cls._style(DIM, f"          {context}") + "\n")

    @classmethod
    def debug_extra(cls, payload: dict[str, Any]) -> None:
        with cls._lock:
            cls._break_open_line()
            cls._write(cls._style(DIM, dumps(payload, default=str)) + "\n")

    @classmethod
    def exception_traceback(cls) -> None:
        if not cls.debug:
            return
        with cls._lock:
            cls._break_open_line()
            traceback.print_exc(file=cls.stream)

    @classmethod
    def summary(
        cls,
        *,
        duration_s: float,
        records: int,
        output: str,
        digest: str | None = None,
    ) -> None:
        with cls._lock:
            cls._break_open_line()
            cls._write("\n")
            cls._write(cls._style(BOLD, f"Done in {duration_s:.1f}s") + "\n")
            cls._write(f"  records   {records}\n")
            cls._write(f"  warnings  {cls.warnings}\n")
            cls._write(f"  errors    {cls.errors}\n")
            if digest:
                cls._write(f"  archive   {output}\n")
                cls._write(f"  sha256    {digest}\n")
            else:
                cls._write(f"  output    {output}\n")
