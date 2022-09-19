"""Collect GitHub URLs for display in the command-line interface."""

from typing import Dict

COLON = ":"
DASH = "-"
SPACE = " "
NEWLINE = "\n"
NEWLINE_NEWLINE = "\n\n"

PROJECTS = {
    "gatorgrade": "https://github.com/GatorEducator/gatorgrade",
    "gatorgrader": "https://github.com/GatorEducator/gatorgrader",
}


def get_github_projects(projects: Dict[str, str] = PROJECTS) -> str:
    """Create a GitHub repository string for all specified projects."""
    # create an empty project_version_str that will be appended
    # to with information about each project and its GitHub URL
    project_version_str = ""
    # iterate through the provided projects and display:
    # 1) the name of the project
    # 2) the GitHub URL for the project
    for project_name in projects.keys():
        current_project_version_str = (
            DASH
            + SPACE
            + project_name
            + COLON
            + SPACE
            + projects[project_name]
            + NEWLINE_NEWLINE
        )
        project_version_str = project_version_str + current_project_version_str
    return project_version_str
