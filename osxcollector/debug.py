"""Debug helpers."""

from __future__ import annotations

DEBUG_MODE = False


def debugbreak() -> None:
    """Break into pdb when DEBUG_MODE is enabled."""
    if DEBUG_MODE:
        import pdb

        pdb.set_trace()
