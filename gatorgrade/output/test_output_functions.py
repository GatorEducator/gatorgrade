"""Test suite for output_functions.py."""
import pytest
from output import output_functions

def test_list_to_string_function():
    """Test list to string function in output tools"""

    list = ['test', 'test2', 'test9', 'puddle']
    expected_string = "test test2 test3 test9 puddle"
    actual_list = output_tools.get_simple_command_string(list)

    assert expected_list == actual_list