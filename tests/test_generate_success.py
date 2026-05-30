"""Test the generate_config function in a perfect situation."""

from pathlib import Path
from typing import Any, Generator

import pytest
import typer

from gatorgrade.generate.generate import generate_config


@pytest.fixture(name="testing_dir")
def setup_files(
    tmp_path: Path,
) -> Generator[Path, None, None]:
    """Perform the setup for the directory for the tests."""
    # given this file structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()
    python_file = src_dir / "test.py"
    python_file.write_text("import sys")
    writing_dir = tmp_path / "writing"
    writing_dir.mkdir()
    reflection = writing_dir / "reflection.md"
    reflection.write_text("# Reflection")
    yield tmp_path


def test_generate_config_create_gatorgrade_yml(
    testing_dir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test to see that gatorgrade_yml file exist in file structure."""
    # when generate_config is called
    generate_config(["src"], str(testing_dir))
    capsys.readouterr()
    # then gatorgrade.yml is created
    gatorgrade_yml = testing_dir / "gatorgrade.yml"
    assert gatorgrade_yml.is_file()


def test_generate_config_creates_gatorgrade_yml_with_dir_in_user_input(
    testing_dir: Any, capsys: pytest.CaptureFixture[str]
) -> None:
    """Test to see if input matches directory."""
    # when generate_config is called
    generate_config(["src"], str(testing_dir))
    capsys.readouterr()
    # then gatorgrade.yml is created
    gatorgrade_yml = testing_dir / "gatorgrade.yml"
    assert "src/test.py" in gatorgrade_yml.open().read()


def test_generate_config_creates_gatorgrade_yml_without_dir_not_in_user_input(
    testing_dir: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Test to see if input does not match directory."""
    # when generate_config is called
    generate_config(["writing"], str(testing_dir))
    capsys.readouterr()
    # then gatorgrade.yml is created
    gatorgrade_yml = testing_dir / "gatorgrade.yml"
    assert "src/test.py" not in gatorgrade_yml.open().read()
    assert "writing/reflection.md" in gatorgrade_yml.open().read()


def test_generate_success_message(
    capsys: pytest.CaptureFixture[str], testing_dir: Any
) -> None:
    """Test to see that there is a success message."""
    # given a directory with a file
    src_dir = Path(testing_dir) / "src"
    src_dir.mkdir(exist_ok=True)
    test_file = src_dir / "test.py"
    test_file.write_text("import sys")
    # when generate_config is called with the existing path
    generate_config(["src"], str(testing_dir))
    out, _ = capsys.readouterr()
    # then a success message is printed
    assert "SUCCESS" in out


def test_generate_config_with_no_files_found(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Test that generate_config raises Exit when no files match user input."""
    # given an empty directory
    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    # when generate_config is called with a path that doesn't exist
    with pytest.raises(typer.Exit) as exc_info:
        generate_config(["nonexistent_folder"], str(empty_dir))
    _, err = capsys.readouterr()
    # then it should raise Exit(1) and print a failure message to stderr
    assert exc_info.value.exit_code == 1
    assert "FAILURE: None of the user-provided file paths are" in err
