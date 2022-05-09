"""Tests the parse_config functions """
from gatorgrade.input.parse_config import parse_config


def test_parse_config_gg_check_in_file_context_contains_file():
    """Test whether the input file can run through parse config"""
    config = "tests/input/gatorgrade_one_gg_check_in_file_context.yml"
    output = parse_config(config)
    assert "file.py" in output[0]   
