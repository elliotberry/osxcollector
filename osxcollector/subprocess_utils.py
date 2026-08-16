"""Safe subprocess helpers (never shell=True)."""

from __future__ import annotations

import subprocess
from collections.abc import Sequence


def run_command(
    argv: Sequence[str],
    *,
    timeout: float | None = 30.0,
    text: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command with a fixed argv list and optional timeout."""
    return subprocess.run(
        list(argv),
        check=False,
        capture_output=True,
        text=text,
        timeout=timeout,
        shell=False,
    )
