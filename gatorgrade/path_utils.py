"""Utilities for converting between filesystem paths and portable display paths."""

from pathlib import Path
from typing import Union


def to_filesystem_path(path_input: Union[str, Path]) -> Path:
    """Convert string or Path objects into an OS-native Path."""
    return Path(path_input).expanduser().resolve()


def to_portable_display_path(path_input: Union[str, Path]) -> str:
    """Convert a path into a forward-slash string for reports and check IDs.

    Follows the host's path rules: backslashes become "/" on Windows but are
    kept on Linux and macOS, where they are valid filename characters.
    """
    p = Path(path_input)
    # convert backslashed to forward slashed without making absolute if relative
    return p.as_posix()
