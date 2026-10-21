from pathlib import Path

from path_utils import (
    to_filesystem_path,
    to_portable_display_path,
)

def test_to_filesystem_path_accepts_string() -> None:
    result = to_filesystem_path("example.txt")

    assert isinstance(result, Path)
    assert result == Path("example.txt").expanduser().resolve()

def test_to_filesystem_path_accepts_path_object() -> None:
    input_path = Path("folder") / "example.txt"

    result = to_filesystem_path(input_path)

    assert isinstance(result, Path)
    assert result == input_path.expanduser().resolve()

def test_to_filesystem_path_resolves_relative_path() -> None:
    result = to_filesystem_path("folder/example.txt")

    assert result.is_absolute()