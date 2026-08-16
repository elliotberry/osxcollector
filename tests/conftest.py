"""Shared test fixtures."""

from __future__ import annotations

from collections.abc import Iterator

import pytest

from osxcollector.console import Console
from osxcollector.logging_jsonl import Logger


@pytest.fixture(autouse=True)
def reset_logger_and_console() -> Iterator[None]:
    Console.reset()
    Logger.reset()
    yield
    Console.reset()
    Logger.reset()
