from sys import stdout
import pytest
import output_functions
from colorama import init, Fore, Back, Style


@pytest.fixture()
def test_output_shows_green():
    out = (f"{Fore.GREEN}\u2714") 


    assert "{Fore.GREEN}\u2714" in out

'''
def test_output_shows_red():




def test_output_shows_yellow():




def test_result():

'''