"""Utilities for converting between filesystem paths and portable display paths."""

from pathlib import Path
from typing import Union


def to_filesystem_path(path_input: Union[str, Path]) -> Path:
    """Convert string or Path objects into an OS-native Path."""
    return Path(path_input).expanduser().resolve()


def to_portable_display_path(path_input: Union[str, Path]) -> str:
    """Convert a path into a portable forward-slash normalized string.

    Guarantees consistent JSON/Markdown output and check ID hashing across operating systems.
    """
    p = Path(path_input)
    # Convert backslashed to forward slashed without making absolute if relative
    return p.as_posix()
