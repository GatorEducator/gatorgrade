"""Tests for the path utility helpers."""

from pathlib import Path

from path_utils import (
    to_filesystem_path,
    to_portable_display_path,
)


def test_to_filesystem_path_accepts_string() -> None:
    """Verify a string input is converted into a Path."""
    result = to_filesystem_path("example.txt")

    assert isinstance(result, Path)
    assert result == Path("example.txt").expanduser().resolve()


def test_to_filesystem_path_accepts_path_object() -> None:
    """Verify a Path object input is converted into a resolved Path."""
    input_path = Path("folder") / "example.txt"

    result = to_filesystem_path(input_path)

    assert isinstance(result, Path)
    assert result == input_path.expanduser().resolve()


def test_to_filesystem_path_resolves_relative_path() -> None:
    """Verify a relative path resolves to an absolute path."""
    result = to_filesystem_path("folder/example.txt")

    assert result.is_absolute()


def test_to_filesystem_path_expands_home_directory(
    monkeypatch,
    tmp_path: Path,
) -> None:
    """Verify a leading tilde expands to the home directory."""
    monkeypatch.setenv("HOME", str(tmp_path))

    result = to_filesystem_path("~/example.txt")

    assert result == (tmp_path / "example.txt").resolve()


def test_to_portable_display_path_uses_forward_slashes() -> None:
    """Verify the display path uses forward slashes as separators."""
    input_path = Path("folder") / "subfolder" / "file.txt"

    result = to_portable_display_path(input_path)

    assert result == "folder/subfolder/file.txt"


def test_to_portable_display_path_does_not_make_path_absolute() -> None:
    """Verify a relative path stays relative in the display output."""
    result = to_portable_display_path("folder/file.txt")

    assert result == "folder/file.txt"
    assert not result.startswith("/")


def test_to_portable_display_path_handles_filename() -> None:
    """Verify a bare filename is returned unchanged."""
    assert to_portable_display_path("README.md") == "README.md"


def test_to_portable_display_path_handles_current_directory() -> None:
    """Verify the current directory is displayed as a single dot."""
    assert to_portable_display_path(".") == "."


def test_to_filesystem_path_handles_current_directory() -> None:
    """Verify the current directory resolves to an absolute path."""
    result = to_filesystem_path(".")

    assert result == Path.cwd()
