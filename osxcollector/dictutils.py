"""Deep dictionary helpers."""

from __future__ import annotations

from typing import Any


class DictUtils:
    """Helpers for deep traversal of nested dict/list structures."""

    @classmethod
    def _link_path_to_chain(cls, path: Any) -> list[Any] | tuple[Any, ...] | set[Any]:
        if path == "":
            return []
        if isinstance(path, (list, tuple, set)):
            return path
        return path.split(".")

    @classmethod
    def _get_deep_by_chain(cls, x: Any, chain: Any, default: Any = None) -> Any:
        if chain == []:
            return default
        try:
            for link in chain:
                try:
                    x = x[link]
                except (KeyError, TypeError):
                    x = x[int(link)]
        except (KeyError, TypeError, ValueError):
            x = default
        return x

    @classmethod
    def get_deep(cls, x: Any, path: Any = "", default: Any = None) -> Any:
        chain = cls._link_path_to_chain(path)
        return cls._get_deep_by_chain(x, chain, default=default)
