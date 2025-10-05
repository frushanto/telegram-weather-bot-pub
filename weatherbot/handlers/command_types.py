"""Type helpers for Telegram command handlers."""

from __future__ import annotations

from typing import Iterable, Tuple, TypeAlias

CommandArgs: TypeAlias = Tuple[str, ...]


def normalize_command_args(raw_args: Iterable[object] | None) -> CommandArgs:
    """Convert raw command arguments into a typed tuple of strings."""

    if not raw_args:
        return ()

    normalized: list[str] = []
    for value in raw_args:
        if value is None:
            continue
        normalized.append(str(value))
    return tuple(normalized)


__all__ = ["CommandArgs", "normalize_command_args"]
