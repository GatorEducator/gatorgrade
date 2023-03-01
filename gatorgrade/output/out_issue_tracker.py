"""Create or rewrite a GitHub issue tracker message about json or markdown report."""

import os
from typing import List
from typing import Union

from pathlib import Path

import rich
from github import Github
from gatorgrade.input.in_file_path import parse_yaml_file


def authenticate() -> Union[None, Github]:
    """Create GitHub objects"""
    # Only write issue tracker message when running in GitHub Action
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Create an instance with GitHub Action Automatic Token to access to GitHub REST API
        token = os.environ["GITHUB_TOKEN"]
        github_api = Github(token)
        # Get the full of Repo like repos/repo1/
        repository_full_name = os.environ.get("GITHUB_REPOSITORY")
        return github_api, repository_full_name
    else:
        # TODO: Provide ability to run locally
        return None


def parse_config(config_file: Path):
    """Find needed information from configuration file"""


def create_issue(
    github_object: Github,
    repo_name: str,
    issue_name: str,
    issue_body: str = "",
    labels: List[str] = [],
) -> bool:
    """Create a new issue.

    Args:
        github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
        repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
        issue_name(str): The name (i.e. title) is used to create a issue
        issue_body(str): content used to make issue body
        labels(list of str): labels that will be attached into the issue
    """

    repo = github_object.get_repo(repo_name)
    repo.create_issue(title=issue_name, body=issue_body, labels=labels + ["Gatorgrade"])
    return True


def rewrite_issue(
    github_object: Github,
    repo_name: str,
    new_issue_name: str = "Gatorgrade: Insight Report",
    new_issue_body: str = "",
    old_issue_name: str = "",
) -> bool:
    """
    Rewrite an issue that already existed.

    Args:
        github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
        repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
        new_issue_name(str): The new name (i.e. title) is used to replace the old name
        new_issue_body(str): the new content used to replace the old issue body
        old_issue_name(str): The name of the issue you want to edit
    """
    repo = github_object.get_repo(repo_name)
    find_issue = False
    for issue in repo.get_issues():
        if issue.title == old_issue_name:
            issue.edit(new_issue_name, new_issue_body)
            # Allow rewrite all the issues which share the same issue name
            find_issue = True
    if find_issue:
        return True
    rich.print(f"\n[red] WARNING: issue called {new_issue_name}, rewrite skipped")
    return False


def update_issue(
    github_object: Github,
    repo_name: str,
    added_issue_body: str = "",
    issue_name: str = "",
):
    """
    Update an issue by adding material in comment.

    Args:
        github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
        repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
        added_issue_body(str): the new content used to replace the old issue body
        issue_name(str): The name of the issue you want to edit
    """
    repo = github_object.get_repo(repo_name)
    find_issue = False
    for issue in repo.get_issues():
        if issue.title == issue_name:
            issue.create_comment(added_issue_body)
            # Allow rewrite all the issues which share the same issue name
            find_issue = True
    if find_issue:
        return True
    rich.print(f"\n[red] WARNING: issue called {issue_name}, rewrite skipped")
    return False


def run_issue_tracker_out(
    issue_name: str = "Gatorgrade: Insight Report", issue_body: str = ""
):
    """Access to issue tracker, it's the main function."""
    api_object, repo_name = authenticate()

    # Can't get valid github object so exit this program
    if not api_object:
        rich.print(
            "\n[red] WARNING: issue tracker report will only work in GitHub Action, skipped creating issue."
        )
        # TODO: add error msg
        return None
    create_issue(api_object, repo_name, "Updated Issue", "Hello Dog")


if __name__ == "__main__":
    run_issue_tracker_out()
