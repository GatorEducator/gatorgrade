"""This module tests the json output functionality"""

# Import needed libraries
import pytest
from typer.testing import CliRunner

from gatorgrade import main

runner = CliRunner()

@pytest.mark.parametrize(
    "assignment_path",
    [
        ("tests/test_assignment")
    ],
)
def test_report_flag_creates_file_output(assignment_path, tmp_path, chdir):
    """Check if json output creates an output .json file after it's run"""
    chdir(assignment_path)
    runner.invoke(main.app, ["--report", f"{tmp_path}/output.json"])
    # "output.json" is generated in the root directory
    file_path = tmp_path / "output.json"
    assert file_path.is_file()

@pytest.mark.parametrize(
    "assignment_path",
    [
        ("tests/test_assignment")
    ],
)
def test_report_flag_creates_valid_json_file_output(assignment_path, tmp_path, chdir):
    """Check if json output creates an output .json file after it's run"""
    import json
    chdir(assignment_path)
    runner.invoke(main.app, ["--report", f"{tmp_path}/output.json"])
    # "output.json" is generated in the root directory
    file_path = tmp_path / "output.json"
    try:
        json.loads(open(file_path).read())
    except ValueError:
        pytest.fail(f"\"{file_path}\" is not valid JSON.")