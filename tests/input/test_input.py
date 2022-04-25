from gatorgrade.input.in_file_path import parse_config

def test_parse_config_gg_check_in_file_context_contains_file():
    config = "tests/input/gatorgrade_one_gg_check_in_file_context.yml"
    output = parse_config(config)
    assert "file.py" in output[0]  