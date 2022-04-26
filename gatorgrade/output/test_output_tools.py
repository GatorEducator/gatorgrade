"""Test suite for output_tools.py."""

import pytest
from output import output_tools

def test_list_to_string_function():
    """Test list to string function in output tools"""

    list = ['test', 'test2', 'test9', 'puddle']
    expected_string = "test test2 test3 test9 puddle"
    actual_string = output_tools.get_simple_command_string(list)

    assert expected_string == actual_string
