# Import needed libraries
import pytest
from pathlib import Path


def test_generate_should_create_gatorgrade_yml_file(tmp_path, capsys):
    """Check if the generate.py creates a gatorgrade.yml file in the root directory after it's run"""
    
    # Given a lab directory contains all of the files and folders that user inputted when calling generate.py
    root_directory = tmp_path / "lab3"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    readme_file = root_directory / "README.md"
    readme_file.write_text("# Lab 3")

    github_directory = root_directory / ".github"
    github_directory.mkdir()

    config_directory = root_directory / "config"
    config_directory.mkdir()

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.mkdir()

    # gatorgrade_yml = root_directory / "gatorgrade.yml"
    # gatorgrade_yml.write_text("Setup: ")

    with capsys.disabled():
        print(root_directory)

    # When we call the modularized version of "generate.py" with two arguments

    # generate_config(["src", "README.md"], root_directory)

    # Then "gatrograde.yml" is generated in the root directory
    file_path = Path(root_directory / "gatorgrade.yml")
    assert file_path.is_file()



