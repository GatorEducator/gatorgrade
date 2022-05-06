"""Pytest fixtures for testing various functions in GatorGrade"""
import pytest
import os

@pytest.fixture
def chdir():
    """Changes working directory to a specified directory then changes back to base directory."""
    prev_dir = os.getcwd()

    def chdir(change_to):
        os.chdir(change_to)

    yield chdir

    os.chdir(prev_dir)
