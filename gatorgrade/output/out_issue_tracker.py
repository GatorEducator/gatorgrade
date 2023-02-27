"""Create or rewrite a GitHub issue tracker message about json or markdown report"""

import os
from github import Github
from typing import Union, List

def authenticate() -> Union[None, Github]:
    # Only write issue tracker message when running in GitHub Action
    if os.environ.get("GITHUB_ACTIONS") == "true":
        # Create an instance with GitHub Action Automatic Token to access to GitHub REST API
        token = os.environ['GITHUB_TOKEN']
        github_api = Github(token)
        # Get the full of Repo like repos/repo1/
        repository_full_name = os.environ.get('GITHUB_REPOSITORY')
        return github_api, repository_full_name
    else:
        # TODO: Provide ability to run locally
        return None

def create_issue(github_object:Github,repo_name:str, issue_name:str = "Gatorgrade: Insight Report",issue_body:str = "",labels:List[str]= []):
    """Create a new issue

    Args:
        github_object(GitHub): An authenticated GitHub object allows to interact with GitHub REST API
        repo_name(str): A whole name of repo following in the format : `repositories/repo-A`
    """

    repo = github_object.get_repo(repo_name)
    # TODO: add github issue body
    repo.create_issue(title= issue_name,body = issue_body, labels=labels + ["Gatorgrade"] )
    

def update_issue(github_object:Github,repo_name:str, new_issue_name:str = "Gatorgrade: Insight Report",new_issue_body:str = "", target_label_name: str = "Gatorgrade"):
    # TODO: add github issue body
    repo = github_object.get_repo(repo_name)
    # Find target issue by target label to rewrite it(default: Gatorgrade)
    # TODO: conflict may happen when there are multiple issues with target label. They may be re-written with the same content
    for issue in repo.get_issues():
        for label in issue.get_labels():
            if label.name == target_label_name:
                issue.edit(new_issue_name,new_issue_body)



        # TODO: try to target issue by names
            pass

def run_issue_tracker_out():
    """Access to issue tracker"""
    api_object, repo_name = authenticate()

    # Can't get valid github object so exit this program
    if not api_object:
        # TODO: add error msg
        return None
    update_issue(api_object,repo_name,"Updated Issue","Hello Dog")

if __name__ == "__main__":
    run_issue_tracker_out()