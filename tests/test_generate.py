# Import needed libraries
import pytest
from pathlib import Path
import yaml

# PyYAML function needed for creating a mock "gatorgrade.yml" file
def str_representer(dumper, data):
    if data.count("\n") > 0:
        return dumper.represent_scalar("tag:yaml.org,2002:str", data, style="|")

    return dumper.represent_scalar("tag:yaml.org,2002:str", data)


def test_generate_should_create_gatorgrade_yml_file(tmp_path):
    """Check if the generate.py creates a gatorgrade.yml file in the root directory after it's run"""

    # Given a lab directory contains all of the files and folders that user inputted when calling generate.py
    root_directory = tmp_path / "Lab-03"
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
    reflection_file.write_text("# Reflection on Lab 03")

    gatorgrade_yml = root_directory / "gatorgrade.yml"
    gatorgrade_yml.write_text("Setup: ")

    # When we call the modularized version of "generate.py" with two arguments

    # generate_config(["src", "README.md"], root_directory)

    # Then "gatrograde.yml" is generated in the root directory
    file_path = Path(root_directory / "gatorgrade.yml")
    assert file_path.is_file()


def test_generated_gatorgrade_yml_file_should_contain_correct_paths_when_successfully_ran(
    tmp_path,
):
    """Check if gatorgrade.yml contains correct paths when successfully created"""

    # Given an assignment directory that contains all of the folders and files that user inputted when calling generate.py
    root_directory = tmp_path / "Practical-01"
    root_directory.mkdir()

    github_directory = root_directory / ".github"
    github_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    test_file_1 = src_directory / "test_file_1.py"
    test_file_1.write_text("import sys")

    test_file_2 = src_directory / "test_file_2.py"
    test_file_2.write_text("import sys")

    input_directory = src_directory / "input"
    input_directory.mkdir()
    input_file = input_directory / "input.txt"
    input_file.write_text("Test input")

    output_directory = src_directory / "output"
    output_directory.mkdir()
    output_file = output_directory / "output.txt"
    output_file.write_text("Test output")

    tests_directory = root_directory / "tests"
    tests_directory.mkdir()
    test_file = tests_directory / "test_file.py"
    test_file.write_text("import pytest")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Practical 01")

    readme_file = root_directory / "README.md"
    readme_file.write_text("# Practical 01")

    pyproject_file = root_directory / "pyproject.toml"
    pyproject_file.write_text("[tool.poetry]")

    # When we call the modularized version of "generate.py" with two arguments

    # generate_config(["src", "README.md"], root_directory)

    # Generate a mock "gatorgrade.yml" for testing purposes
    setup_dict = {
        "setup": "# add setup commands here\n",
    }

    files_list = [
        {
            "src/input/input.txt": [
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        },
        {
            "src/output/output.txt": [
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        },
        {
            "src/main.py": [
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        },
        {
            "src/test_file_1.py": [
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        },
        {
            "src/test_file_2.py": [
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        },
        {
            "README.md": [
                {
                    "description": "Complete all TODOs",
                    "check": "MatchFileFragment",
                    "options": {"fragment": "TODO", "count": 0, "exact": True},
                }
            ]
        },
    ]

    yaml.add_representer(str, str_representer)

    gatorgrade_yml = root_directory / "gatorgrade.yml"
    gatorgrade_yml.write_text(
        yaml.dump_all(
            (setup_dict, files_list), default_flow_style=False, sort_keys=False
        )
    )

    file = gatorgrade_yml.open()
    file_text = file.read()

    # Then the "gatorgrade.yml" contains correct paths to user inputted directories and files
    assert "- src/input/input.txt:" in file_text
    assert "- src/output/output.txt:" in file_text
    assert "- src/main.py:" in file_text
    assert "- src/test_file_1.py:" in file_text
    assert "- src/test_file_2.py:" in file_text
    assert "- README.md:" in file_text
