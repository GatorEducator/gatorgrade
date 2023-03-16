"""Create or rewrite a GitHub issue tracker message about json or markdown report."""

import os
from pathlib import Path
from typing import List
from typing import Tuple

import rich
from github import Github

from gatorgrade.input.in_file_path import parse_yaml_file


def authenticate() -> Tuple[Github, str]:
    """Create GitHub objects."""
    # Only write issue tracker message when running in GitHub Action
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Create an instance with GitHub Action Automatic Token to access to GitHub REST API
        token = os.environ["GITHUB_TOKEN"]
        github_api = Github(token)
        # Get the full of Repo like repos/repo1/
        repository_full_name = os.environ.get("GITHUB_REPOSITORY")
        return github_api, repository_full_name
    else:
        raise PermissionError(
            "WARNING: issue tracker report only works in GitHub Action, skipped creating issue."
        )
        # TODO: Provide ability to run locally


def parse_config(config_file: Path):
    """Find needed information from configuration file."""
    # TODO
    pass


class issueExecute:
    """Execute changes related to issue(s)."""

    @staticmethod
    def create_issue(
        github_object: Github,
        repo_name: str,
        issue_name: str,
        issue_body: str,
        labels: List[str] = [],
    ) -> bool:
        """
        Create a new issue.

        Args:
            github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
            repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
            issue_name(str): The name (i.e. title) is used to create a issue
            issue_body(str): content used to make issue body
            labels(list of str): labels that will be attached into the issue
        """
        repo = github_object.get_repo(repo_name)
        repo.create_issue(
            title=issue_name, body=issue_body, labels=labels + ["Gatorgrade"]
        )
        print(f"\n[green] 🏖️ Successfully create an issue called {issue_name}")
        return True

    @staticmethod
    def rewrite_issue(
        github_object: Github,
        repo_name: str,
        issue_name: str,
        new_issue_body: str = "",
    ) -> bool:
        """
        Rewrite an issue that already existed.

        Args:
            github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
            repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
            issue_name(str): The name of the issue you want to edit
            new_issue_body(str): the new content used to replace the old issue body
        """
        repo = github_object.get_repo(repo_name)
        find_issue = False
        for issue in repo.get_issues():
            if issue.title == issue_name:
                issue.edit(issue_name, new_issue_body)
                # Allow rewrite all the issues which share the same issue name
                find_issue = True
        if find_issue:
            rich.print(
                f"\n[green] 🏖️ Successfully rewrite all the issues called{issue_name}"
            )
            return True
        rich.print(f"\n[red] WARNING: issue called {issue_name}, rewrite skipped")
        return False

    @staticmethod
    def update_issue(
        github_object: Github,
        repo_name: str,
        issue_name: str,
        added_issue_body: str = "",
    ):
        """
        Update an issue by adding material in comment.

        Args:
            github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
            repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
            issue_name(str): The name of the issue you want to edit
            added_issue_body(str): the new content used to replace the old issue body
        """
        repo = github_object.get_repo(repo_name)
        find_issue = False
        for issue in repo.get_issues():
            if issue.title == issue_name:
                issue.create_comment(added_issue_body)
                # Allow rewrite all the issues which share the same issue name
                find_issue = True
        if find_issue:
            print(f"\n[green] 🏖️ Successfully update issues called {issue_name}")
            return True
        rich.print(f"\n[red] WARNING: issue called {issue_name}, update skipped")
        return False


class issueMode:
    """Determine steps to do to issue(s)."""

    def __init__(self) -> None:
        """Get Github base information."""
        # TODO: move authentication function out of this class for a better modularization
        self.api_object, self.repo_name = authenticate()

    def stack_issue_list_mode(
        self,
        issue_name: str = "Gatorgrade: Insight Report",
        issue_body: str = "",
        labels: List[str] = [],
    ):
        """Create a new issue instead of editing the same issue."""
        if not self.__check_issue_existence(issue_name):
            issueExecute.create_issue(
                self.api_object, self.repo_name, issue_name, issue_body, labels
            )
            # TODO: decide return type
            return
        issueExecute.rewrite_issue(
            self.api_object, self.repo_name, issue_name, issue_body
        )
        return

    def rewrite_issue_mode(
        self,
        issue_name: str = "Gatorgrade: Insight Report",
        issue_body: str = "",
        labels: List[str] = [],
    ):
        """Create a new issue if there is no issue, otherwise rewrite the new issue."""
        if not self.__check_issue_existence(issue_name):
            issueExecute.create_issue(
                self.api_object, self.repo_name, issue_name, issue_body, labels
            )
            # TODO: decide return type
            return
        issueExecute.rewrite_issue(
            self.api_object, self.repo_name, issue_name, issue_body
        )
        return

    def stack_issue_mode(
        self,
        issue_name: str = "Gatorgrade: Insight Report",
        issue_body: str = "",
        labels: List[str] = [],
    ):
        """Create a new issue if there is no issue, otherwise add new comments on the same issue."""
        if not self.__check_issue_existence(issue_name):
            issueExecute.create_issue(
                self.api_object, self.repo_name, issue_name, issue_body, labels
            )
            # TODO: decide return type
            return
        issueExecute.update_issue(
            self.api_object, self.repo_name, issue_name, issue_body
        )

    def __check_issue_existence(self, issue_name: str) -> bool:
        """Check if an issue exist or not."""
        repo = self.api_object.get_repo(self.repo_name)
        for issue in repo.get_issues():
            if issue.title == issue_name:
                return True
        return False


if __name__ == "__main__":
    a_issue = issueMode()
    a_issue.rewrite_issue_mode()
