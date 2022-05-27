# Global imports
"""Test the generate_config function in a perfect situation."""
import os
import pytest
from pathlib import Path
from gatorgrade.generate.generate import generate_config


@pytest.fixture(name="testing_dir")
def setup_files(tmp_path):
    """Setup directory for tests"""
    # Given this file structure
    src_dir = tmp_path / "src"
    src_dir.mkdir()

    python_file = src_dir / "test.py"
    python_file.write_text("import sys")

    writing_dir = tmp_path / "writing"
    writing_dir.mkdir()

    reflection = writing_dir / "reflection.md"
    reflection.write_text("# Reflection")
    yield tmp_path


def test_generate_config_create_gatorgrade_yml(testing_dir):
    """Test to see that gatorgrade_yml file exist in file structure"""
    # When generate_config is called
    generate_config(["src"], str(testing_dir))
    # Then gatorgrade.yml is created
    gatorgrade_yml = testing_dir / "gatorgrade.yml"
    assert gatorgrade_yml.is_file()


def test_generate_config_creates_gatorgrade_yml_with_dir_in_user_input(testing_dir):
    """Test to see if input matches directory"""
    # When generate_config is called
    generate_config(["src"], str(testing_dir))
    # Then gatorgrade.yml is created
    gatorgrade_yml = testing_dir / "gatorgrade.yml"
    assert os.path.normpath("src/test.py") in gatorgrade_yml.open().read()


def test_generate_config_creates_gatorgrade_yml_without_dir_not_in_user_input(
    testing_dir,
):
    """Test to see if input does not match directory"""
    # When generate_config is called
    generate_config(["writing"], str(testing_dir))
    # Then gatorgrade.yml is created
    gatorgrade_yml = testing_dir / "gatorgrade.yml"
    assert os.path.normpath("src/test.py") not in gatorgrade_yml.open().read()
    assert os.path.normpath("writing/reflection.md") in gatorgrade_yml.open().read()


def test_generate_success_message(capsys, testing_dir):
    """Test to see that there is a success message"""
    # When generate_config is called
    generate_config(["src"], str(testing_dir))
    out, _ = capsys.readouterr()
    # Then a success message is printed
    assert "SUCCESS" in out
