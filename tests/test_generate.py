"""This module tests the generate.py functionality"""

import pytest
import typer

from gatorgrade.generate.generate import generate_config


def test_generate_should_create_gatorgrade_yml_file(tmp_path):
    """Check if generate.py creates a gatorgrade.yml file in the root directory after it's run"""

    # Given a directory contains all the files and folders user inputted when calling generate.py
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

    # When we call the modularized version of "generate.py" with two arguments
    generate_config(["src", "README.md"], str(root_directory))

    # Then "gatorgrade.yml" is generated in the root directory
    file_path = root_directory / "gatorgrade.yml"
    assert file_path.is_file()


def test_generated_gatorgrade_yml_file_should_contain_correct_paths_when_successfully_ran(
    tmp_path,
):
    """Check if gatorgrade.yml contains correct paths when successfully created"""

    # Given an assignment directory that contains all of the folders
    # and files that user inputted when calling generate.py
    root_directory = tmp_path / "Practical-01"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    test_file_1 = src_directory / "test_file_1.py"
    test_file_1.write_text("import sys")

    input_directory = src_directory / "input"
    input_directory.mkdir()
    input_file = input_directory / "input.txt"
    input_file.write_text("Test input")

    output_directory = src_directory / "output"
    output_directory.mkdir()
    output_file = output_directory / "output.txt"
    output_file.write_text("Test output")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Practical 01")

    readme_file = root_directory / "README.md"
    readme_file.write_text("# Practical 01")

    # When we call the modularized version of "generate.py" with two arguments
    generate_config(["src", "README.md"], str(root_directory))

    # Then the "gatorgrade.yml" contains correct paths to user inputted directories and files
    file = root_directory / "gatorgrade.yml"
    file_text = file.open().read()

    assert "src/input/input.txt" in file_text
    assert "src/output/output.txt" in file_text
    assert "src/main.py" in file_text
    assert "src/test_file_1.py" in file_text
    assert "README.md" in file_text


def test_generate_should_produce_warning_message_when_some_user_inputted_files_dont_exist(
    tmp_path, capsys
):
    """Check if gatorgrade.yml is created with existing file paths
    when some user-provided file paths don't exist and if generate.py outputs a warning message
    """

    # Given an assignment directory that contains some folders
    root_directory = tmp_path / "Practical-02"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()

    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Practical 02")

    tests_directory = root_directory / "tests"
    tests_directory.mkdir()
    test_file = tests_directory / "test_file.py"
    test_file.write_text("import pytest")

    # When we call the modularized version of "generate.py"
    # with two arguments, but README.md doesn't exist
    generate_config(["src", "README.md"], str(root_directory))

    # Then "gatorgrade.yml" is created with existing file paths and produce warning
    file = root_directory / "gatorgrade.yml"
    file_text = file.open().read()
    captured = capsys.readouterr()

    assert "src/main.py" in file_text
    assert "README.md" not in file_text
    assert "file path is not FOUND!" in captured.out


def test_generate_should_throw_an_error_when_none_of_user_provided_files_exist(
    tmp_path, capsys
):
    """Check if generate.py throws an error and produce a failure message
    when none of user provided file paths exist in the root directory"""

    # Given an assignment directory
    root_directory = tmp_path / "Lab-01"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    input_directory = src_directory / "input"
    input_directory.mkdir()
    input_file = input_directory / "input.txt"
    input_file.write_text("Test input")

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Lab 01")

    # When we call the modularized version of "generate.py"
    # with two arguments, but none of the files exist in the root directory

    with pytest.raises(typer.Exit) as exc_info:
        generate_config(["tests", "README.md"], str(root_directory))

    _, err = capsys.readouterr()

    # Then "gatorgrade.yml" should not be generated and generate.py should throw a typer.Exit
    file = root_directory / "gatorgrade.yml"
    assert not file.is_file()
    assert "'gatorgrade.yml' is NOT generated" in err
    assert exc_info.value.exit_code == 1


def test_run_path_unify(tmp_path):
    """Check if the function correctly appends a separator to run_path if it doesn't end with one"""

    # Given an assignment directory that contains all of the folders and files that user inputted when calling generate.py
    root_directory = tmp_path / "Practical-01"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    test_file_1 = src_directory / "test_file_1.py"
    test_file_1.write_text("import sys")

    input_directory = src_directory / "input"
    input_directory.mkdir()
    input_file = input_directory / "input.txt"
    input_file.write_text("Test input")

    output_directory = src_directory / "output"
    output_directory.mkdir()
    output_file = output_directory / "output.txt"
    output_file.write_text("Test output")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Practical 01")

    readme_file = root_directory / "README.md"
    readme_file.write_text("# Practical 01")

    # Verify that the generate_config function works correctly
    generate_config(["src", "writing", "README.md"], str(root_directory))

    # Then the "gatorgrade.yml" contains correct paths to user inputted directories and files
    file = root_directory / "gatorgrade.yml"
    file_text = file.open().read()

    # assert run_path == expected_run_path

    assert "src/input/input.txt" in file_text
    assert "src/output/output.txt" in file_text
    assert "src/main.py" in file_text
    assert "src/test_file_1.py" in file_text
    assert "README.md" in file_text


def test_ignore_folder_starting_with_double_underscore(tmp_path):
    """Ignore folder and file starting with double underscore"""

    # Given an assignment directory that contains all of the folders
    # and files that user inputted when calling generate.py
    root_directory = tmp_path / "Practical-01"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    task_directory = root_directory / "__task"
    task_directory.mkdir()

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    test_file_1 = src_directory / "test_file_1.py"
    test_file_1.write_text("import sys")

    input_directory = src_directory / "input"
    input_directory.mkdir()
    input_file = input_directory / "__input.txt"
    input_file.write_text("Test input")

    output_directory = src_directory / "__output"
    output_directory.mkdir()
    output_file = output_directory / "output.txt"
    output_file.write_text("Test output")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Practical 01")

    readme_file = root_directory / "README.md"
    readme_file.write_text("# Practical 01")

    # When we call the modularized version of "generate.py" with two arguments
    generate_config(["src", "Practical-01", "README.md"], str(root_directory))

    # Then the "gatorgrade.yml" contains correct paths to user inputted directories and files
    file = root_directory / "gatorgrade.yml"
    file_text = file.open().read()

    assert "__task" not in file_text
    assert "src/input/__input.txt" not in file_text
    assert "src/__output" not in file_text


def test_ignore_folder_starting_with_single_dot(tmp_path):
    """Ignore folder starting with a single dot and not with double dot"""

    # Given an assignment directory that contains all of the folders
    # and files that user inputted when calling generate.py
    root_directory = tmp_path / "Practical-01"
    root_directory.mkdir()

    src_directory = root_directory / "src"
    src_directory.mkdir()

    task_directory = root_directory / ".task"
    task_directory.mkdir()

    main_py = src_directory / "main.py"
    main_py.write_text("import sys")

    test_file_1 = src_directory / "test_file_1.py"
    test_file_1.write_text("import sys")

    input_directory = src_directory / "input"
    input_directory.mkdir()
    input_file = input_directory / ".input.txt"
    input_file.write_text("Test input")

    output_directory = src_directory / "output"
    output_directory.mkdir()
    output_file = output_directory / "output.txt"
    output_file.write_text("Test output")

    writing_directory = root_directory / "writing"
    writing_directory.mkdir()
    reflection_file = writing_directory / "reflection.md"
    reflection_file.write_text("# Reflection on Practical 01")

    readme_file = root_directory / "README.md"
    readme_file.write_text("# Practical 01")

    # When we call the modularized version of "generate.py" with two arguments
    generate_config(
        ["src", "task", "Practical-01", "README.md", ".."], str(root_directory)
    )

    # Then the "gatorgrade.yml" contains correct paths to user inputted directories and files
    file = root_directory / "gatorgrade.yml"
    file_text = file.open().read()

    assert ".task" not in file_text
    assert "src" in file_text
    assert "src/input/.input.txt" not in file_text


# pytest.main()
