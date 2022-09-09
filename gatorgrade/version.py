"""Extract version information for display in various aspects of the command-line interface."""

from importlib.metadata import version

COLON = ":"
SPACE = " "


def get_project_version(project: str) -> str:
    """Extract the version information for a project and return formatted version string."""
    project_version_str = version(project)
    return project + COLON + SPACE + project_version_str


def get_gatorgrade_version() -> str:
    """Determine and return the information about GatorGrade's version."""
    gatorgrade_version_str = get_project_version("gatorgrade")
    return gatorgrade_version_str


def get_gatorgrader_version() -> str:
    """Determine and return the information about GatorGrade's version."""
    gatorgrader_version_str = get_project_version("gatorgrader")
    return gatorgrader_version_str
