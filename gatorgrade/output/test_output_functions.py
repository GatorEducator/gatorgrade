"""Test suite for output_functions.py."""

import pytest
from output import output_functions

def test_receive_command_function_returns_no_error():
    """Make sure the receive function in output_functions.py runs"""

    results = []
    results.append(("file.txt", [('No TODOs in text', True, ''),
        ('Has 5 comments', False, 'Found 3 Fragments in file.'),
        ('Removed dependencies', True, '')]))
    results.append(("file2.txt", [('No TODOs in text', False,
        'Found 5 fragments in file2.'), ('Has API call', True, ''),
        ('Contains 20 comments', True, '')]))

    try:
        receive_command(results)
    except Exception as exc:
        assert False, f"'Command receive function' raised an exception {exc}"
