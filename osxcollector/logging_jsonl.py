"""JSON-lines logging for forensic records."""

from __future__ import annotations

import sys
import threading
from json import dumps
from traceback import extract_tb
from typing import Any, TextIO

from osxcollector.debug import DEBUG_MODE, debugbreak


class Logger:
    """Write JSON records to an output file and mirror errors to stderr."""

    output_file: TextIO = sys.stdout
    lines_written = 0
    _lock = threading.Lock()

    @classmethod
    def set_output_file(cls, output_file: TextIO) -> None:
        cls.output_file = output_file

    @classmethod
    def log_dict(cls, record: dict[str, Any]) -> None:
        payload = dict(record)
        with cls._lock:
            payload.update(Logger.Extra.extras)
            try:
                cls.output_file.write(dumps(payload, default=str))
                cls.output_file.write("\n")
                cls.output_file.flush()
                cls.lines_written += 1
            except OSError as e:
                debugbreak()
                cls.log_exception(e)

    @classmethod
    def log_warning(cls, message: str) -> None:
        cls.log_dict({"osxcollector_warn": message})
        if DEBUG_MODE:
            sys.stderr.write(f"[WARN] {message} - {Logger.Extra.extras!r}\n")

    @classmethod
    def log_error(cls, message: str) -> None:
        cls.log_dict({"osxcollector_error": message})
        sys.stderr.write(f"[ERROR] {message} - {Logger.Extra.extras!r}\n")

    @classmethod
    def log_exception(cls, e: BaseException, message: str = "") -> None:
        exc_type, _, exc_traceback = sys.exc_info()
        to_print = f"{message} {e!s} {exc_type} {extract_tb(exc_traceback)}"
        cls.log_error(to_print)

    class Extra:
        """Context manager that attaches key/value pairs to every logged line."""

        extras: dict[str, Any] = {}

        def __init__(self, key: str, val: Any) -> None:
            self.key = key
            self.val = val

        def __enter__(self) -> Logger.Extra:
            Logger.Extra.extras[self.key] = self.val
            if DEBUG_MODE:
                sys.stderr.write(dumps({self.key: self.val}, default=str))
                sys.stderr.write("\n")
            return self

        def __exit__(self, exc_type: Any, value: Any, traceback: Any) -> None:
            del Logger.Extra.extras[self.key]
