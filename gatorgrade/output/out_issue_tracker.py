"""Create or rewrite a GitHub issue tracker message about json or markdown report."""

import os
import sys
from pathlib import Path
from typing import Dict
from typing import List
from typing import Tuple

import rich
from github import Github

from gatorgrade.input.parse_config import parse_yaml_file
import pytest




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
                # Rewrite all the issues which share the same issue name
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

    def __init__(self, api_object: Github, repo_name: str) -> None:
        """
        Get Github base information.

        Args:
        api_object(Github): An object of Github
        repo_name(str): Name of the Github repository
        """
        self.api_object, self.repo_name = api_object, repo_name
        self.mode_list = ["rewrite", "multi", "comment"]

    def multi_issue_mode(
        self,
        issue_name: str = "Gatorgrade: Insight Report",
        issue_body: str = "",
        labels: List[str] = [],
    ):
        """
        Create a new issue instead of editing the same issue.

        Args:
            issue_name(str): Name of the issue
            issue_body(str): Body of the issue
            labels(list): A list of the issue
        """
        # All the issue mode methods have to end with _issue_mode and follow the same argument format
        issueExecute.create_issue(
            self.api_object, self.repo_name, issue_name, issue_body, labels
        )
        return

    def rewrite_issue_mode(
        self,
        issue_name: str = "Gatorgrade: Insight Report",
        issue_body: str = "",
        labels: List[str] = [],
    ):
        """
        Create a new issue if there is no issue, otherwise rewrite the new issue.

        Args:
            issue_name(str): Name of the issue
            issue_body(str): Body of the issue
            labels(list): A list of the issue
        """
        # All the issue mode methods have to end with _issue_mode and follow the same argument format

        first_operation = False
        if not self.__check_issue_existence(issue_name):
            first_operation = True
            issueExecute.create_issue(
                self.api_object, self.repo_name, issue_name, issue_body, labels
            )
            return first_operation
        issueExecute.rewrite_issue(
            self.api_object, self.repo_name, issue_name, issue_body
        )
        return first_operation

    def comment_issue_mode(
        self,
        issue_name: str = "Gatorgrade: Insight Report",
        issue_body: str = "",
        labels: List[str] = [],
    ):
        """
        Create a new issue if there is no issue, otherwise add new comments on the same issue.

        Args:
            issue_name(str): Name of the issue
            issue_body(str): Body of the issue
            labels(list): A list of the issue
        """
        # All the issue mode methods have to end with _issue_mode and follow the same argument format

        first_operation = False
        if not self.__check_issue_existence(issue_name):
            first_operation = True
            issueExecute.create_issue(
                self.api_object, self.repo_name, issue_name, issue_body, labels
            )
            return first_operation
        issueExecute.update_issue(
            self.api_object, self.repo_name, issue_name, issue_body
        )
        return first_operation
    def __check_issue_existence(self, issue_name: str) -> bool:
        """
        Check if an issue exist or not.

        Args:
            issue_name(str): name of the issue
        """
        repo = self.api_object.get_repo(self.repo_name)
        for issue in repo.get_issues():
            if issue.title == issue_name:
                return True  # pragma: no cover
        return False      # pragma: no cover


class issueReport:
    """Represents an issue tracker report."""

    def __init__(self, config_file: Path, report_content: str) -> None:
        """
        Get necessary inf.

        Args:
            config_file(Path): Path to the configuration file
            report_content(str): Content of the Github Issue report
        """
        self.config = config_file
        self.report_content = report_content
        self.github_object, self.repo_name = self._authenticate()
        self.user_data = self.__parse_config_data()

    def report(self):
        """Create a report in Github Issue Tracker."""
        # user doesn't define any inf about issue report, skip issue report
        if not self.user_data:
            return False

        gatorgrade_issue = issueMode(self.github_object, self.repo_name)
        user_chosen_mode = self.user_data["mode"]
        supported_modes = gatorgrade_issue.mode_list
        # Make sure user chooses the supported mode
        if user_chosen_mode not in supported_modes:
            rich.print(
                f"\n[red] {user_chosen_mode} is not in the supported mode list {supported_modes}"
            )
            sys.exit(1)

        rich.print("\n[green] 🔍 Creating issue report(s)")
        # Transform user chosen mode name to the full mode method name
        mode_method_name = user_chosen_mode + "_issue_mode"
        # Get mode method in issueMode class by method name
        mode_method = getattr(gatorgrade_issue, mode_method_name)

        # Create default NONE arguments to unify function arguments
        issue_name, labels = None, []
        if "options" in self.user_data:
            # If one option doesn't exist, method will be triggered with a method default value
            options = self.user_data["options"]
            issue_name = options["issue_name"] if "issue_name" in options else None
            labels = options["labels"] if "labels" in options else []

        # Run the mode method to execute issue report
        mode_method(issue_name, self.report_content, labels)
        return True

    def _authenticate() -> Tuple[Github, str]:
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

    def __parse_config_data(self) -> Dict:
        """Parse the configuration file specified in the `config_file` attribute and and return issue report related data."""
        parsed_yaml_file = parse_yaml_file(self.config)
        # the parsed YAML file contains some contents in a list and thus
        if len(parsed_yaml_file) > 0:
            # find 'issue_report' dictionary. It's in the first dict of data list
            parse_con = parsed_yaml_file[0]
            if "issue_report" in parse_con:
                return parse_con["issue_report"]
        return dict()
