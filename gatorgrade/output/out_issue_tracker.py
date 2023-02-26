"""Create or rewrite a GitHub issue tracker message about json or markdown report"""

import os
from github import Github
from typing import Union
def authenticate() -> Union(None, Github):
    # Only write issue tracker message when running in GitHub Action
    if os.environ.get("CI") == "true":
        # Create an instance with GitHub Action Automatic Token to access to GitHub REST API
        github_api = Github("secrets.GITHUB_TOKEN")
        return github_api
    else:
        return None

def create_issue(github_object,epo_name:str, title:str ,body:str):

    for event in github_object.get_events():
        print(event.repo.name)
    

def run_issue_tracker_out():
    """Access to issue tracker and edit it"""
    api_object: Github = authenticate()

    # Can't get valid github object so exit this program
    if not api_object:
        return None
    create_issue()