"""Guard contributor and agent commands, references, and coverage."""

import re
import subprocess
import sys
from pathlib import Path

import pytest
import toml

ROOT_INDEX = 1
ROOT = Path(__file__).resolve().parents[ROOT_INDEX]
CONFIG_FILE = "pyproject.toml"
GUIDE_FILE = "CONTRIBUTING.md"
AGENT_FILE = "AGENTS.md"
ENCODING = "utf-8"
TASK_PATTERN = re.compile(
    r"uv run (?:(?:--no-sync|--extra [\w-]+) )*task ([\w-]+)"
)
LINK_PATTERN = re.compile(r"\[[^\]]+\]\(([^\s)]+)\)")
FRAGMENT_SEPARATOR = "#"
SCHEME_SEPARATOR = ":"
FIRST_INDEX = 0
DOCUMENT_PARAMETER = "document"
PREFIX_PARAMETER = "prefix"
TASK_PREFIXES = [
    "uv run task ",
    "uv run --no-sync task ",
    "uv run --extra auto-hint task ",
]
UNKNOWN_TASK = "nonexistent-agent-task"
VALID_TASK = "all"
GUIDE_LINK = "[guide](CONTRIBUTING.md)"
GUIDE_CONTENT = "# Guide\n"
MINIMUM_COVERAGE = 95
MINIMUM_DIRECT_COVERAGE = 75
DIRECT_THRESHOLD = "directtestedfailunder"
TOOL = "tool"
TASKIPY = "taskipy"
TASKS = "tasks"
VARIABLES = "variables"
THRESHOLD = "coveragefailunder"
COVERAGE = "coverage"
RUN = "run"
BRANCH = "branch"
CONFIG = toml.loads((ROOT / CONFIG_FILE).read_text(encoding=ENCODING))
WORKFLOW_FILE = ".github/workflows/main.yml"
SYNC_PREFIX = "run: uv sync"
LOCKED_FLAG = "--locked"
CLASS_NAMING_RULE = "N801"
CLASS_NAMING_EXAMPLES = [
    ("class invalid_name: pass\n", False),
    ("class ValidName: pass\n", True),
]
EXPECTED_EXCLUSIONS = [
    "pragma: no cover",
    "def __repr__",
    "raise AssertionError",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "if TYPE_CHECKING:",
    "@abstractmethod",
]


def assert_documented_tasks(text: str) -> None:
    """Reject unknown task names in the documented uv command forms."""
    commands = set(TASK_PATTERN.findall(text))
    assert commands
    assert commands <= CONFIG[TOOL][TASKIPY][TASKS].keys()


def assert_agent_links(text: str, root: Path) -> None:
    """Reject missing local files linked with inline Markdown links."""
    for target in LINK_PATTERN.findall(text):
        filename = target.split(FRAGMENT_SEPARATOR)[FIRST_INDEX]
        if filename and SCHEME_SEPARATOR not in filename:
            assert (root / filename).is_file(), target


@pytest.mark.parametrize(DOCUMENT_PARAMETER, [GUIDE_FILE, AGENT_FILE])
def test_documented_tasks_exist(document: str) -> None:
    """Reject nonexistent tasks in contributor and agent instructions."""
    assert_documented_tasks((ROOT / document).read_text(encoding=ENCODING))


@pytest.mark.parametrize(PREFIX_PARAMETER, TASK_PREFIXES)
def test_documented_tasks_reject_unknown_names(prefix: str) -> None:
    """Reject a stale task name and accept its corrected command."""
    with pytest.raises(AssertionError):
        assert_documented_tasks(prefix + UNKNOWN_TASK)
    assert_documented_tasks(prefix + VALID_TASK)


def test_agent_links_exist() -> None:
    """Keep inline local instruction references connected to real files."""
    assert_agent_links((ROOT / AGENT_FILE).read_text(encoding=ENCODING), ROOT)


def test_agent_links_reject_missing_files(tmp_path: Path) -> None:
    """Reject a dangling reference and accept it after creating its target."""
    with pytest.raises(AssertionError):
        assert_agent_links(GUIDE_LINK, tmp_path)
    (tmp_path / GUIDE_FILE).write_text(GUIDE_CONTENT, encoding=ENCODING)
    assert_agent_links(GUIDE_LINK, tmp_path)


def test_coverage_requirement_is_preserved() -> None:
    """Keep the documented coverage minimum and branch measurement enabled."""
    threshold = CONFIG[TOOL][TASKIPY][VARIABLES][THRESHOLD]
    assert int(threshold) >= MINIMUM_COVERAGE
    direct = CONFIG[TOOL][TASKIPY][VARIABLES][DIRECT_THRESHOLD]
    assert int(direct) >= MINIMUM_DIRECT_COVERAGE
    assert CONFIG[TOOL][COVERAGE][RUN][BRANCH] is True


def test_coverage_pipeline_is_preserved() -> None:
    """Keep coverage tasks connected to the protected measurement settings."""
    tasks = CONFIG[TOOL][TASKIPY][TASKS]
    coverage = tasks["test-coverage"]
    command = coverage["cmd"]
    assert coverage["use_vars"] is True
    assert "--cov=gatorgrade" in command.split()
    assert "--cov-branch" in command.split()
    assert "--cov-fail-under={coveragefailunder}" in command.split()
    assert (
        tasks["all"] == "task check && task test && task test-coverage-check"
    )
    assert tasks["test-coverage-check"]["use_vars"] is True
    assert (
        "--threshold {directtestedfailunder}"
        in tasks["test-coverage-check"]["cmd"]
    )
    assert CONFIG[TOOL][COVERAGE][RUN]["source"] == ["gatorgrade"]
    assert CONFIG[TOOL][COVERAGE][RUN]["omit"] == [
        "tests/*",
        "**/__init__.py",
    ]
    assert CONFIG[TOOL][COVERAGE]["report"]["fail_under"] >= MINIMUM_COVERAGE
    assert CONFIG[TOOL][COVERAGE]["report"]["exclude_lines"] == (
        EXPECTED_EXCLUSIONS
    )
    assert CONFIG[TOOL][COVERAGE]["report"].get("exclude_also", []) == []


def test_ci_dependency_resolution_is_locked() -> None:
    """Require dependency installation jobs to honor the committed lockfile."""
    workflow = (ROOT / WORKFLOW_FILE).read_text(encoding=ENCODING)
    commands = [
        line.strip()
        for line in workflow.splitlines()
        if line.strip().startswith(SYNC_PREFIX)
    ]
    assert commands
    assert all(LOCKED_FLAG in command.split() for command in commands)


@pytest.mark.parametrize(("source", "accepted"), CLASS_NAMING_EXAMPLES)
def test_class_naming_policy(source: str, accepted: bool) -> None:
    """Verify class naming rejection and recovery with the real linter."""
    assert CLASS_NAMING_RULE in CONFIG[TOOL]["ruff"]["lint"]["select"]
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "ruff",
            "check",
            "--config",
            str(ROOT / CONFIG_FILE),
            "--select",
            CLASS_NAMING_RULE,
            "-",
        ],
        input=source,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    assert (result.returncode == 0) is accepted
    if not accepted:
        assert CLASS_NAMING_RULE in result.stdout
