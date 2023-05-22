"""Implement mock APIs for github for the purposes of testing."""

# !Note: this module does get checked by linters


class MockGH:
    """Supports the used mock functionalities of GitHub API."""

    def __init__(self) -> None:
        """Contain name and repos."""
        self.name = "gh-mock-api"
        self.repos = {}

    def get_repo(self, repo_name: str):
        """Mimics the return of a repo object.

        Args:
            repo_name (str): name of the repo to create and return
        """
        if repo_name not in self.repos:
            self.repos[repo_name] = MockRepo(repo_name)
        return self.repos[repo_name]


class MockRepo:
    """Create mock repos with posting functionalities."""

    def __init__(self, name: str) -> None:
        """Contain info for repo."""
        self.name = name
        # create empty issue to start with
        self.issues = [MockIssue("empty", "empty", number=1, labels=["empty"])]
        self.issues_last_index = 0
        self.pulls = [MockPullRequest("empty", "empty", "empty", "empty", 1)]
        self.pulls_last_index = 0
        self.contents = {}

    def create_issue(self, title: str, body: str, labels=None):
        """Mock the create issue function."""
        self.issues_last_index += 1
        issue = MockIssue(title, body, labels=labels, number=self.issues_last_index)
        self.issues = [issue] + self.issues
        return issue

    def get_issues(self, state="all"):
        """Return all the issues."""
        return self.issues

    def get_issue(self, number: int):
        """Return one specific issue based on number."""
        return self.issues[number - 1]

    def create_pull(self, title: str, body: str, base: str, head: str):
        """Create a mock git pull."""
        self.pulls_last_index += 1
        pull_request = MockPullRequest(title, body, base, head, self.pulls_last_index)
        self.pulls = [pull_request] + self.pulls
        return pull_request

    def get_pulls(self, state="all"):
        """Get all the mock git pulls."""
        return self.pulls

    def get_pull(self, number: int):
        """Get one specific mock git pull according to number."""
        return self.pulls[number - 1]

    def get_contents(self, path: str, branch=None):
        """Get full contents of one pull."""
        if "." in path:
            return self.contents[path]
        contents = []
        for key, content_file in self.contents.items():
            if key.startswith(path):
                contents.append(content_file)
        return contents

    def create_file(self, path, commit_message, content, branch):
        """Create a file in mock repo."""
        content_file = MockContentFile(path, commit_message, content, branch)
        self.contents[path] = content_file
        return {"content": content_file}

    def update_file(self, path, commit_message, new_content, sha, branch):
        """Update a file in mock repo."""
        new_file = MockContentFile(path, commit_message, new_content, branch)
        new_file.sha = sha
        self.contents[path] = new_file
        return {"content": new_file}

    def delete_file(self, path, commit_message, sha, branch):
        """Remove a file in mock repo."""
        self.contents.pop(path, None)


class MockIssue:
    """Create mock issue tracker with body, title, and labels information."""

    def __init__(self, title: str, body: str, number: int, labels=None) -> None:
        """Include all the inf about a mock issue."""
        self.title = title
        self.body = body
        self.number = number
        self.labels = []
        if labels:
            for label in labels:
                self.labels.append(MockLabel(label))
        self.comments = []
        self.state = "open"

    def create_comment(self, body: str):
        """Create a mock comment in an issue."""
        self.comments.append(MockComment(body))

    def get_comments(self):
        """Return all the comments."""
        return self.comments

    def add_to_labels(self, label_name: str):
        """Add one label in label lists."""
        self.labels.append(MockLabel(label_name))

    def edit(self, title: str, issue_body: str):
        """Replace old title or issue body with new ones."""
        self.title = title
        self.body = issue_body


class MockLabel:
    """Create mock label with name infomation."""

    def __init__(self, name: str) -> None:
        """Get name of a label."""
        self.name = name


class MockComment:
    """Create mock comment with body infomation."""

    def __init__(self, body: str) -> None:
        """Get body of a comment."""
        self.body = body


class MockPullRequest:
    """Create mock pull request with body, title, head, and base branches."""

    def __init__(
        self, title: str, body: str, base: str, head: str, number: int
    ) -> None:
        """Get all the inf about a pull request including title, body, number."""
        self.title = title
        self.body = body
        self.base = base
        self.head = head
        self.number = number
        self.comments = []
        self.labels = []
        self.state = "open"

    def create_issue_comment(self, body: str):
        """Add a new comment into the comment list."""
        self.comments.append(MockComment(body))

    def get_issue_comments(self):
        """Get all the comments."""
        return self.comments

    def edit(self, state: str):
        """Edit the state of a pull request."""
        self.state = state


class MockContentFile:
    """Create a mock content file with path, commit message, contents and branches."""

    def __init__(
        self, path: str, commit_message: str, contents: str, branch: str
    ) -> None:
        """Get all the inf about one content file."""
        self.path = path
        self.decoded_content = contents.encode(encoding="utf-8")
        self.commit_message = commit_message
        self.branch = branch
        self.type = "file"
        self.sha = ""
