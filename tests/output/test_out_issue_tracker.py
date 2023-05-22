from tests.output.mock_api import github_mock_api
from gatorgrade.output.out_issue_tracker import issueReport, issueExecute,issueMode
import pytest
from pathlib import Path
import yaml

from gatorgrade.input.in_file_path import parse_yaml_file

##########################
#### issueReport test ####
##########################

@pytest.fixture
def mocked_issueReport(monkeypatch):
    def mock_authenticate(*args, **kwargs):
        return github_mock_api.MockGH(), "test_repo"

    monkeypatch.setattr(issueReport, "_authenticate", mock_authenticate)
    # Return a lambda function that instantiates MyClass with the patched attribute
    return issueReport


def test_issue_report_none_with_no_config_file(mocked_issueReport):
    """Check there is no user data if no configuration file is given."""

    invalid_report = mocked_issueReport(Path("wrong_path"), "")
    # The user data should be a null dictionary
    assert invalid_report.user_data == dict()


def test_report_none_with_config_in_config_file(mocked_issueReport, tmp_path):
    """Check there is no report if there is no issue report related data given in config file."""

    tem_cofig_path = Path(tmp_path / "config_invalid.yml")

    # Given there is no issue_report key in the configuration file
    config_content = {"setup": None}

    # Create a temporary file for test purpose
    with open(tem_cofig_path, "w") as file:
        yaml.dump(config_content,file)

    invalid_report = mocked_issueReport(tem_cofig_path, "")
    # The user data should be a null dictionary
    assert invalid_report.user_data == dict()


def test_report_data_exists_with_config_data(mocked_issueReport, tmp_path):
    """Check use_data attribute has user_data if appropriate config file is given"""

    tem_cofig_path = Path(tmp_path/"config_valid.yml")

    # Given there is issue_report key in the configuration file
    config_content = {
        "setup": None,
        "issue_report": {
            "mode": "comment",
            "options": {
                "issue_name": "Gatorgrade: Insight Report from YAML",
                "labels": ["Hello-World", "YAMLtmd"],
            },
        }
    }

    # Create a temporary file for test purpose
    with open(tem_cofig_path, "w") as file:
        yaml.dump(config_content,file)

        # read the contents of the specified file using the default
        # encoding and then parse that file using the yaml package
    with open(tem_cofig_path, 'r') as file:
        data = yaml.safe_load(file)

    assert data == config_content
    valid_report = mocked_issueReport(tem_cofig_path, "")
    assert valid_report.user_data == config_content["issue_report"]

def test_wrong_user_mode_should_fail(mocked_issueReport,tmp_path):
    """Test system exits failingly if the user chosen mode is not in the supported mode list."""
    tem_cofig_path = Path(tmp_path/"config_valid.yml")

    # Given there is wrong mode in the configuration file
    config_content = {
        "setup": None,
        "issue_report": {
            "mode": "wrong",
            "options": {
                "issue_name": "Gatorgrade: Insight Report from YAML",
                "labels": ["Hello-World", "YAMLtmd"],
            },
        }
    }

    # Create a temporary file for test purpose
    with open(tem_cofig_path, "w") as file:
        yaml.dump(config_content,file)

        # read the contents of the specified file using the default
        # encoding and then parse that file using the yaml package
    with open(tem_cofig_path, 'r') as file:
        data = yaml.safe_load(file)

    valid_report = mocked_issueReport(tem_cofig_path, "")
    with pytest.raises(SystemExit) as e:
        valid_report.report()
    assert e.type == SystemExit
    assert e.value.code == 1

def test_issueReport_reports_successfully_without_option(mocked_issueReport,tmp_path):
    """Test report method generates an issue successfully without any option being specified in config file."""
    tmp_config = Path(tmp_path/"config_valid.yml")

    # Given there is issue_report key in the configuration file
    config_content = {
        "setup": None,
        "issue_report": {
            "mode": "comment",
        }
    }

    # Create a temporary file for test purpose
    with open(tmp_config, "w") as file:
        yaml.dump(config_content,file)

    mocked_instance = mocked_issueReport(tmp_config,"Hello World")
    assert mocked_instance.repo_name == "test_repo"
    # report method should return True
    assert mocked_instance.report()

def test_issueReports_fails_without_user_data(mocked_issueReport,tmp_path):
    """Test the report method should fail without any issue_report inf in configuration file."""
    tmp_config = Path(tmp_path/"config_invalid.yml")

    # Given there is no issue report inf specified in configuration file
    config_content = {
        "setup": None,
    }

    # Create a temporary file for test purpose
    with open(tmp_config, "w") as file:
        yaml.dump(config_content,file)

    mocked_instance = mocked_issueReport(tmp_config,"Hello World")
    assert mocked_instance.repo_name == "test_repo"
    assert mocked_instance.report() == False

def test_issueReport_reports_successfully_with_option(mocked_issueReport,tmp_path):
    """Test report method generates an issue successfully with options being specified in config file."""
    tmp_config = Path(tmp_path/"config_valid.yml")

    # Given specific options in config file
    config_content = {
        "setup": None,
        "issue_report": {
            "mode": "multi",
            "options": {
                "issue_name": "Gatorgrade: Insight Report from YAML",
                "labels": ["Hello-World", "YAMLtmd"],
            },
        }
    }

    # Create a temporary file for test purpose
    with open(tmp_config, "w") as file:
        yaml.dump(config_content,file)

    mocked_instance = mocked_issueReport(tmp_config,"Hello World")
    assert mocked_instance.repo_name == "test_repo"

    # report method should return True
    assert mocked_instance.report()

def test_issueReport_report_fails_with_wrong_mode(mocked_issueReport,tmp_path):
    """Test the issue reports falsely with a wrong mode other than the three supported modes."""
    tmp_config = Path(tmp_path/"config_valid.yml")

    # Given a wrong mode in issue report
    config_content = {
        "setup": None,
        "issue_report": {
            "mode": "wrong",
            "options": {
                "issue_name": "Gatorgrade: Insight Report from YAML",
                "labels": ["Hello-World", "YAMLtmd"],
            },
        }
    }

    # Create a temporary file for test purpose
    with open(tmp_config, "w") as file:
        yaml.dump(config_content,file)

    # When trying to call report method
    with pytest.raises(SystemExit) as exit_inf:
        mocked_instance = mocked_issueReport(tmp_config,"Hello World")
        mocked_instance.report()
    # A exit code 1 will be raised
    assert exit_inf.value.code == 1
###########################
#### issueExecute test ####
###########################



def test_create_issue_successfully():
    """Check if issue is created if all the required info is given."""
    status = issueExecute.create_issue(github_object=github_mock_api.MockGH(),repo_name="test_repo",issue_name="Insight",issue_body="hello world")
    assert status

def test_rewrite_issue_fails():
    """Check the rewrite_issue function should fail when issue doesn't exist."""
    # Rewrite issue directly without create an issue before
    status = issueExecute.rewrite_issue(github_object=github_mock_api.MockGH(),repo_name="test_repo",issue_name="Insight",new_issue_body="hello world")
    assert status is False

def test_rewrite_issue_pass():
    """Check the issue is rewritten successfully."""
    github_mock_object = github_mock_api.MockGH()

    # Given a existing issue and rewrite its body
    issueExecute.create_issue(github_object = github_mock_object,repo_name="test_repo",issue_name="Insight",issue_body="hello world")
    status = issueExecute.rewrite_issue(github_object = github_mock_object,repo_name="test_repo",issue_name="Insight",new_issue_body="rewrite hello world")

    # The issue body should be the updated version
    issues = github_mock_object.get_repo("test_repo").get_issues()
    found_issue = False
    for issue in issues:
         if issue.title == "Insight":
            found_issue = True
            assert issue.body == "rewrite hello world"
    
    # Assert the created issue is found
    assert found_issue
    # Then the return value of rewrite_issue should be True
    assert status

def test_update_issue_fails():
    """Check the update_issue function should fail when issue doesn't exist."""
    # Rewrite issue directly without create an issue before
    status = issueExecute.update_issue(github_object=github_mock_api.MockGH(),repo_name="test_repo",issue_name="Insight",added_issue_body="hello world")
    assert status is False

def test_update_issue_pass():
    """Check the issue is updated successfully."""
    github_mock_object = github_mock_api.MockGH()

    # Given a existing issue and rewrite its body
    issueExecute.create_issue(github_object = github_mock_object,repo_name="test_repo",issue_name="Insight",issue_body="hello world")
    status = issueExecute.update_issue(github_object = github_mock_object,repo_name="test_repo",issue_name="Insight",added_issue_body="hello world again")

    # The issue body should be the updated version
    issues = github_mock_object.get_repo("test_repo").get_issues()
    found_issue = False
    found_comment = False
    for issue in issues:
         if issue.title == "Insight":
            found_issue = True
            for comment in issue.comments:
            
                if comment.body == "hello world again":
                    found_comment = True
    
    # Assert the created issue is found
    assert found_issue and found_comment
    # Then the return value of rewrite_issue should be True
    assert status


###########################
##### issueMode test ######
###########################

def test_multi_issue_mode_pass():
    """Check the multi_issue_mode function in class issueMode works well."""
    github_mock_object = github_mock_api.MockGH()
    issue_mode_instance = issueMode(api_object = github_mock_object,repo_name="test_repo")
    issue_mode_instance.multi_issue_mode(issue_name="Insight",issue_body="hello world")
    assert github_mock_object.repos["test_repo"]

def test_rewrite_issue_mode_creates_new_issue():
    """Check the rewrite_issue_mode function in class issueMode creates a new issue."""
    github_mock_object = github_mock_api.MockGH()
    issue_mode_instance = issueMode(api_object = github_mock_object,repo_name="test_repo")
    create_issue_flag = issue_mode_instance.rewrite_issue_mode(issue_name="Insight",issue_body="hello world")
    assert create_issue_flag == True

def test_rewrite_issue_mode_rewrites_old_issue():
    """Check the rewrite_issue_mode function in class issueMode rewrites a old issue instead of creating a new issue."""
    github_mock_object = github_mock_api.MockGH()
    issue_mode_instance = issueMode(api_object = github_mock_object,repo_name="test_repo")
    # First time call rewrite_issue_mode
    create_issue_flag = issue_mode_instance.rewrite_issue_mode(issue_name="Insight",issue_body="hello world")
    # a new issue should be generated
    assert create_issue_flag
    # Second time call rewrite_issue_mode
    create_issue_flag = issue_mode_instance.rewrite_issue_mode(issue_name="Insight",issue_body="hello world")

    # An old issue should be rewritten and the method should return false
    assert create_issue_flag == False

def test_comment_issue_mode_creates_new_issue():
    """Check the rewrite_issue_mode function in class issueMode creates a new issue."""
    github_mock_object = github_mock_api.MockGH()
    issue_mode_instance = issueMode(api_object = github_mock_object,repo_name="test_repo")
    create_issue_flag = issue_mode_instance.comment_issue_mode(issue_name="Insight",issue_body="hello world")
    assert create_issue_flag == True

def test_comment_issue_mode_creates_comments_old_issue():
    """Check the rewrite_issue_mode function in class issueMode comments a old issue instead of creating a new issue."""
    github_mock_object = github_mock_api.MockGH()
    issue_mode_instance = issueMode(api_object = github_mock_object,repo_name="test_repo")
    # First time call comment_issue_mode
    create_issue_flag = issue_mode_instance.comment_issue_mode(issue_name="Insight",issue_body="hello world")
    # a new issue should be generated
    assert create_issue_flag
    # Second time call comment_issue_mode
    create_issue_flag = issue_mode_instance.comment_issue_mode(issue_name="Insight",issue_body="hello world")

    # An old issue should be commented and the method should return false
    assert create_issue_flag == False