from sys import stdout
from output import output_functions
import pytest
from colorama import init, Fore, Style
init()

@pytest.fixture()
def test_output_shows_green(capsys):
    output_functions.sample_output_passing_check()
    out, err = capsys.readouterr()

    assert f"{Fore.GREEN}\u2714" in out
    assert err == ""


def test_output_shows_red(capsys):
    output_functions.sample_output_failing_check()
    out, err = capsys.readouterr()

    assert f"{Fore.RED}" in out
    assert err == ""


def test_output_shows_yellow(capsys):

    output_functions.output_fail_description(desc="missing if statement")
    out, err = capsys.readouterr()

    assert f"{Fore.YELLOW}\u2192" in out
    assert err ==  ""


def test_descrition_in_fail_message(capsys):
    output_functions.output_check_result(file="txt",check=("todos",False,"no ifs "))
    out, err = capsys.readouterr()
    expected_output = "no ifs "
    actual_output = out
    assert  expected_output in actual_output
    assert "" in err 

def test_false_result_returns_X(capsys):
    
    output_functions.output_check_result(file="txt",check=("todos",False,"no ifs "))
    
    out,err = capsys.readouterr()
    
    assert '\u2718' in out
    assert err == ""



def test_style_reset():



    '''
def test_result():







    

Def test_passing_result_has_one_line 


def test_output_will_show_diagnostic


def test_Description_taken_as_argument



def test style reset changes color
'''