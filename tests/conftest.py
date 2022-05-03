import pytest
import os


@pytest.fixture
def chdir():
    prev_dir = os.getcwd()

    def chdir(change_to):
        os.chdir(change_to)

    yield chdir

    os.chdir(prev_dir)
