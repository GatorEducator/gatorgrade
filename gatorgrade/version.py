"""Extract version information for display in various aspects of the command-line interface."""

from importlib.metadata import version


def get_gatorgrade_version() -> str:
    """Determine and return the information about GatorGrade's version."""
    gatorgrade_version_str = version("gatorgrade")
    return gatorgrade_version_str


def get_gatorgrader_version() -> str:
    """Determine and return the information about GatorGrade's version."""
    gatorgrader_version_str = version("gatorgrader")
    return gatorgrader_version_str
