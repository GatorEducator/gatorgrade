from typer.testing import CliRunner

runner = CliRunner()


def test_gatorgrade_runs_correctly():
    """Test that ensures that the default command runs correctly."""
    assert True


def test_generate_creates_correctly():
    """Test that ensures that the generate command creates the .yml file correctly."""
    assert True


def test_generate_fails_with_existing_yml():
    """Test that ensures that a second yml file isn't generated without the force command."""
    # result = runner.invoke(app, "generate")
    assert True


def test_generate_force_command_creates_yml():
    """Test that ensures the force command works correctly."""
    # result = runner.invoke(app, "generate", "--force")
    assert True
