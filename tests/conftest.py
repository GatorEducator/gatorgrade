"""Pytest fixtures for testing various functions in GatorGrade"""

import os
import pytest


@pytest.fixture
def chdir():
    """Changes working directory to a specified directory then changes back to base directory."""
    prev_dir = os.getcwd()

    def do_change(change_to):
        os.chdir(change_to)

    yield do_change

    os.chdir(prev_dir)
