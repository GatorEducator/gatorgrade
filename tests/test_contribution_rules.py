"""Guard documented task names and the existing coverage requirement."""

import re
from pathlib import Path

import toml

ROOT_INDEX = 1
ROOT = Path(__file__).resolve().parents[ROOT_INDEX]
CONFIG_FILE = "pyproject.toml"
GUIDE_FILE = "CONTRIBUTING.md"
ENCODING = "utf-8"
TASK_PATTERN = re.compile(r"uv run (?:--extra [\w-]+ )?task ([\w-]+)")
MINIMUM_COVERAGE = 95
TOOL = "tool"
TASKIPY = "taskipy"
TASKS = "tasks"
VARIABLES = "variables"
THRESHOLD = "coveragefailunder"
COVERAGE = "coverage"
RUN = "run"
BRANCH = "branch"
CONFIG = toml.loads((ROOT / CONFIG_FILE).read_text(encoding=ENCODING))


def test_documented_tasks_exist() -> None:
    """Reject nonexistent task commands in the actual contributor guide."""
    text = (ROOT / GUIDE_FILE).read_text(encoding=ENCODING)
    commands = set(TASK_PATTERN.findall(text))
    assert commands
    assert commands <= CONFIG[TOOL][TASKIPY][TASKS].keys()


def test_coverage_requirement_is_preserved() -> None:
    """Keep the documented coverage minimum and branch measurement enabled."""
    threshold = CONFIG[TOOL][TASKIPY][VARIABLES][THRESHOLD]
    assert int(threshold) >= MINIMUM_COVERAGE
    assert CONFIG[TOOL][COVERAGE][RUN][BRANCH] is True
