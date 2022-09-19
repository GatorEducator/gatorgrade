"""Extract version information for display in various aspects of the command-line interface."""

from importlib.metadata import version
from typing import List

COLON = ":"
DASH = "-"
SPACE = " "
NEWLINE = "\n"
NEWLINE_NEWLINE = "\n\n"


# Projects are hard-coded and may need to be updated if there are
# new dependencies specified inside of the pyproject.toml file.
# With that said, this approach avoids the need to parse the
# dependencies listed in the pyproject.toml file.
PROJECTS = ["gatorgrade", "gatorgrader", "pyyaml", "rich", "typer"]


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


def get_project_versions(project_list: List[str] = PROJECTS) -> str:
    """Create a version string for all specified projects."""
    project_version_str = ""
    for project in project_list:
        current_project_version_str = (
            DASH + SPACE + get_project_version(project) + NEWLINE_NEWLINE
        )
        project_version_str = project_version_str + current_project_version_str
    return project_version_str
