"""Use GatorGrade to run checks and generate helpful output."""

import importlib.metadata
import sys
from enum import Enum
from pathlib import Path
from typing import Optional, Tuple

import typer
from click.core import ParameterSource
from pydantic import ValidationError
from rich.console import Console
from rich.emoji import Emoji
from rich.rule import Rule
from rich.text import Text
from rich.tree import Tree

from gatorgrade.detect import (
    GATORGRADER_DEPENDENCY,
    get_os_release,
    get_platform_info,
    get_python_info,
    print_version_info,
)
from gatorgrade.engine import (
    AUTO_HINT_MODEL_DEFAULT,
    create_auto_hint_engine,
)
from gatorgrade.hint.local_engine import DEFAULT_MODEL_ID
from gatorgrade.hint.remote_engine import REMOTE_MODEL_DEFAULT
from gatorgrade.input.filter import (
    DEFAULT_FILTER_BY,
    DEFAULT_FILTER_FUZZY_THRESHOLD,
    DEFAULT_FILTER_MODE,
    DEFAULT_FILTER_TYPE,
    FilterBy,
    FilterMode,
    FilterType,
    filter_checks,
)
from gatorgrade.input.parse_config import (
    get_config_dir,
    get_due_date,
    get_due_date_aliases_present,
    get_project_name,
    has_due_date_field,
    parse_config,
    resolve_config_path,
)
from gatorgrade.insights import (
    InsightsReport,
    build_insights_report,
    render_json,
    render_text,
)
from gatorgrade.output.output import run_checks
from gatorgrade.report_history import (
    DEFAULT_HISTORY_QUERY_COUNT,
    DEFAULT_HISTORY_REPORT_COUNT,
    DEFAULT_HISTORY_SIZE_MIB,
    filter_checks_by_failed_ids,
    get_all_check_ids,
    get_failed_check_ids,
    get_history_scope,
    get_report_history_directory,
    load_history_reports_with_diagnostics,
)
from gatorgrade.resolve import (
    resolve_system_prompt,
    resolve_validation_rules,
)
from gatorgrade.validate import (
    validate_auto_hint_options,
    validate_baseline_weight,
    validate_filter_failed_last,
    validate_filter_fuzzy_threshold,
    validate_filter_options,
    validate_filter_passed_last,
    validate_github_env,
    validate_insights_input,
    validate_insights_last,
    validate_insights_output,
    validate_output_limit,
    validate_report,
    validate_report_history_count,
    validate_report_history_size,
)

# import the version from the single-source-of-truth module so that
# other modules (e.g., gatorgrade.hint.remote_engine) can import it
# without creating a circular dependency that looks like:
# gatorgrade.main -> gatorgrade.version -> gatorgrade.main
from gatorgrade.version import GATORGRADE_VERSION

# create an app for the Typer-based CLI

# define the emoji that will be prepended to the help message;
# note that this uses a Rich emoji so that it is as platform-
# independent as possible, across three major operating systems
gatorgrade_emoji = Emoji.replace(":crocodile:")

# constants for display of output
NEWLINE = "\n"
TAB = "   "

# create a Typer app that
# --> does not support completion
# --> has a specified help message with an emoji
#     followed by usage instructions for uvx/uv run
app = typer.Typer(
    add_completion=False,
    help=(
        f"{gatorgrade_emoji} Run the GatorGrader checks in the"
        f" specified configuration file."
        f"{NEWLINE}{NEWLINE}"
        "Want to run gatorgrade using uv?"
        f"{NEWLINE}{NEWLINE}"
        f"{TAB}- Without auto-hinting:"
        f"{NEWLINE}"
        f"{TAB}{TAB}- uvx gatorgrade"
        f"{NEWLINE}"
        f"{TAB}{TAB}- uv tool run gatorgrade"
        f"{NEWLINE}"
        f"{TAB}- With auto-hinting:"
        f"{NEWLINE}"
        f"{TAB}{TAB}- uvx --from 'gatorgrade\\[auto-hint]' gatorgrade"
        f" --auto-hint"
        f"{NEWLINE}"
        f"{TAB}{TAB}- uv tool run --from 'gatorgrade\\[auto-hint]'"
        f" gatorgrade --auto-hint"
    ),
)

# create a default console for printing with rich
console = Console()

# define constants used in this module
FILE = "gatorgrade.yml"
FAILURE = 1


# exit message
EXIT_MESSAGE = "Fix these error(s) before running gatorgrade."

# default config directory computed at module load time for display in help
DEFAULT_CONFIG_DIR = str(get_config_dir())
DEFAULT_REPORT_HISTORY_DIR = str(get_report_history_directory())

# cli flag names used in the report
CONFIG_FLAG = "--config"
CONFIG_DIR_FLAG = "--config-dir"
REPORT_FLAG = "--report"
OUTPUT_LIMIT_FLAG = "--output-limit"
BASELINE_WEIGHT_FLAG = "--baseline-weight"
PROGRESS_BAR_FLAG = "--progress-bar"
SHOW_DIAGNOSTICS_FLAG = "--show-diagnostics"
VERBOSE_FLAG = "--verbose"
AUTO_HINT_FLAG = "--auto-hint"
AUTO_HINT_MODEL_FLAG = "--auto-hint-model"
AUTO_HINT_URL_FLAG = "--auto-hint-url"
AUTO_HINT_API_KEY_FLAG = "--auto-hint-api-key"
AUTO_HINT_TRACK_FLAG = "--auto-hint-track"
FILTER_MODE_FLAG = "--filter-mode"
FILTER_BY_FLAG = "--filter-by"
FILTER_TYPE_FLAG = "--filter-type"
FILTER_QUERY_FLAG = "--filter-query"
FILTER_FUZZY_THRESHOLD_FLAG = "--filter-fuzzy-threshold"
FILTER_TOTAL_FLAG = "--filter-total"
FILTER_FAILED_LAST_FLAG = "--filter-failed-last"
FILTER_PASSED_LAST_FLAG = "--filter-passed-last"
FILTER_HISTORY_REPORTS_FLAG = "--filter-history-reports"
FILTER_HISTORY_REPORTS_TOTAL_FLAG = "--filter-history-reports-total"
REPORT_HISTORY_FLAG = "--report-history"
REPORT_HISTORY_MAX_COUNT_FLAG = "--report-history-max-count"
REPORT_HISTORY_MAX_MIB_FLAG = "--report-history-max-mb"
GITHUB_ENV_FLAG = "--github-env"

# labels for rich rule display
CONFIG_ERROR_LABEL = "Configuration Error"
CONFIG_ERROR_PLURAL_LABEL = "Configuration Error(s)"

# version info keys used in the report
GATORGRADE_VERSION_KEY = "gatorgrade_version"
GATORGRADER_VERSION_KEY = "gatorgrader_version"
PYTHON_INFO_KEY = "python_info"
PLATFORM_INFO_KEY = "platform_info"
OS_RELEASE_KEY = "os_release"

# names, defaults, and messages for the insights command
INSIGHTS_COMMAND_NAME = "insights"
ANALYZE_COMMAND_NAME = "analyze"
ANALYZE_HELP = "Alias for the insights command."
INSIGHTS_DEFAULT_LAST = DEFAULT_HISTORY_QUERY_COUNT
INSIGHTS_FILE_ENCODING = "utf-8"
INSIGHTS_HEADING_STYLE = "bold"
INSIGHTS_HEADING_LINES = 3
# a rendered JSON payload always opens with an object brace, which is
# how the readable report is told apart from output that must reach the
# terminal exactly as it was rendered
INSIGHTS_JSON_START = "{"
INSIGHTS_TITLE_STYLES = (
    ("GatorGrade", "bold green"),
    ("Insights", "bold yellow"),
)
INSIGHTS_TABLE_STYLES = (
    (r"(?m)^FOCUS ON THESE.*$", "bold yellow"),
    (r"(?m)^ALL CHECKS.*$", "bold cyan"),
    (r"(?m)^\| RATE .*\|$", "bold cyan"),
    (r"(?m)^\+[-+]+\+$", "dim"),
    (r"(?<=\| )(?:pass|improving|100%)(?= +\|)", "bold green"),
    (r"(?<=\| )(?:fail|declining)(?= +\|)", "bold red"),
    (r"(?<=\| )\d+ failing(?: in a row)?(?= +\|)", "bold red"),
)
INSIGHTS_CONFIG_MISSING_FMT = (
    "The configuration file {} does not exist; "
    "insights needs it to identify this project."
)
INSIGHTS_WROTE_FMT = "Wrote {} insights to {}"
INSIGHTS_WRITE_ERROR_FMT = "Could not write the insights file {}: {}"
INSIGHTS_READ_ERROR_FMT = "Could not read the insights file {}: {}"
INSIGHTS_INVALID_FMT = (
    "The file {} is not a valid insights report; "
    "regenerate it with the insights command."
)
INSIGHTS_LAST_FLAG = "--last"
INSIGHTS_HISTORY_DIR_FLAG = "--history-dir"
INSIGHTS_OUTPUT_FLAG = "--output"
INSIGHTS_SAVE_FLAG = "--save"
INSIGHTS_INPUT_FLAG = "--input"
# a saved report always lands in this directory, created on demand, so
# that a check can require the file at one known path
INSIGHTS_SAVE_DIRECTORY = Path("insights")
INSIGHTS_SAVE_CONFLICT_FMT = (
    "The {} option writes to a chosen path and cannot be combined with {}."
)
INSIGHTS_LAST_PARAMETER = "last"
INSIGHTS_HISTORY_DIR_PARAMETER = "history_dir"
INSIGHTS_INPUT_CONFLICT_FMT = (
    "The {} option analyzes a saved report and cannot be combined with {}."
)
INSIGHTS_CONFLICT_SEPARATOR = " or "


class InsightsFormat(str, Enum):
    """Represent the output formats supported by the insights command."""

    TEXT = "text"
    JSON = "json"


# the saved file is named for the format it holds so that a text report
# and a machine-readable report can sit in the directory together
INSIGHTS_SAVE_NAMES = {
    InsightsFormat.TEXT: "insights.txt",
    InsightsFormat.JSON: "insights.json",
}


def _version_callback(value: bool) -> None:
    """Print the GatorGrade version and exit when --version is provided."""
    if value:
        tree = Tree("Version", guide_style="dim")
        env_tree = Tree("Environment", guide_style="dim")
        print_version_info(console, tree=tree, env_tree=env_tree)
        console.print(tree)
        console.print(env_tree)
        raise typer.Exit()


def _print_verbose_info(  # noqa: PLR0913
    verbose: bool,
    config_path: Path,
    config_dir: Path,
    auto_hint: bool,
    auto_hint_model: str,
    auto_hint_url: Optional[str],
    output_limit: int,
    baseline_weight: int,
    show_diagnostics: bool,
    progress_bar: bool,
    auto_hint_track: bool | None = None,
    filter_query: str | None = None,
    filter_mode: FilterMode = DEFAULT_FILTER_MODE,
    filter_by: FilterBy = DEFAULT_FILTER_BY,
    filter_type: FilterType = DEFAULT_FILTER_TYPE,
    filter_fuzzy_threshold: float = DEFAULT_FILTER_FUZZY_THRESHOLD,
    filter_failed_last: int | None = None,
    filter_passed_last: int | None = None,
    report_history: bool = True,
    report_history_max_count: int = DEFAULT_HISTORY_REPORT_COUNT,
    report_history_max_mib: int = DEFAULT_HISTORY_SIZE_MIB,
) -> None:
    """Print verbose configuration info before running checks.

    When verbose is True, displays a ruled section with
    version info, file paths, and the active CLI arguments.

    Args:
        verbose: Whether verbose mode is enabled.
        config_path: The resolved config file path.
        config_dir: The config directory being used.
        auto_hint: Whether auto-hint mode is enabled.
        auto_hint_model: The auto-hint model identifier.
        auto_hint_url: The remote auto-hint URL, if any.
        output_limit: The output limit value.
        baseline_weight: The baseline weight value.
        show_diagnostics: Whether diagnostics are shown.
        progress_bar: Whether the progress bar is shown.
        auto_hint_track: Whether auto-hint tracking is enabled.
        filter_query: The filter query string, or None.
        filter_mode: The filter mode, or None.
        filter_by: The filter-by field, or None.
        filter_type: The filter type, or None.
        filter_fuzzy_threshold: Fuzzy word-matching threshold.
        filter_failed_last: Number of recent reports for failure filtering.
        filter_passed_last: Number of recent reports for passed filtering.
        report_history: Whether automatic report history is enabled.
        report_history_max_count: Maximum retained report count.
        report_history_max_mib: Maximum retained report size in MiB.

    """
    if not verbose:
        return
    console.print()
    console.print(Rule("Verbose Mode Information", style="green"))
    console.print()
    # version tree (same structure as --version)
    version_tree = Tree("Version", guide_style="dim")
    env_tree = Tree("Environment", guide_style="dim")
    print_version_info(console, tree=version_tree, env_tree=env_tree)
    console.print(version_tree)
    console.print(env_tree)
    # configuration tree
    config = Tree("Configuration", guide_style="dim")
    config.add(f"Config file: {config_path}")
    config.add(f"Config dir: {config_dir}")
    config.add(f"Output limit: {output_limit}")
    config.add(f"Baseline weight: {baseline_weight}")
    config.add(f"Diagnostics: {show_diagnostics}")
    config.add(f"Progress: {progress_bar}")
    config.add(f"Auto-hint: {auto_hint}")
    # auto hinting
    if auto_hint:
        model_display = auto_hint_model
        if auto_hint_model == AUTO_HINT_MODEL_DEFAULT:
            model_display = (
                REMOTE_MODEL_DEFAULT if auto_hint_url else DEFAULT_MODEL_ID
            )
        config.add(f"Model: {model_display}")
        if auto_hint_url:
            config.add(f"Remote URL: {auto_hint_url}")
        config.add(f"Auto-hint track: {auto_hint_track}")
    console.print(config)
    # filtering tree
    filtering = Tree("Filtering", guide_style="dim")
    if filter_query:
        filtering.add(f"Query: {filter_query}")
    filtering.add(f"Mode: {filter_mode.value}")
    filtering.add(f"By: {filter_by.value}")
    filtering.add(f"Type: {filter_type.value}")
    if filter_mode == FilterMode.FUZZY:
        filtering.add(f"Fuzzy threshold: {filter_fuzzy_threshold}")
    if filter_failed_last is not None:
        filtering.add(f"Failed last: {filter_failed_last}")
    if filter_passed_last is not None:
        filtering.add(f"Passed last: {filter_passed_last}")
    console.print(filtering)
    # reports tree
    reports = Tree("Reports", guide_style="dim")
    reports.add(f"History: {report_history}")
    if report_history:
        reports.add(f"Max count: {report_history_max_count}")
        reports.add(f"Max MiB: {report_history_max_mib}")
        reports.add(f"Directory: {DEFAULT_REPORT_HISTORY_DIR}")
    console.print(reports)
    console.print()
    console.print(Rule(style="green"))


@app.callback(invoke_without_command=True)
def gatorgrade(  # noqa: PLR0912, PLR0913, PLR0915
    ctx: typer.Context,
    filename: Path = typer.Option(
        FILE,
        "--config",
        "-c",
        help="Name of the configuration file in YML format.",
    ),
    config_dir: Optional[Path] = typer.Option(
        None,
        "--config-dir",
        "-d",
        help=(
            "Directory for gatorgrade.yml and other configuration files"
            " referenced in gatorgrade.yml's YML frontmatter."
        ),
        show_default=DEFAULT_CONFIG_DIR,
    ),
    filter_query: Optional[str] = typer.Option(
        None,
        "--filter-query",
        help=(
            "Search term for pre-run check filtering. When provided,"
            " the checks matching this query are included or excluded."
            " Requires at least one non-blank character. Runs after any"
            " --filter-failed-last or --filter-passed-last status"
            " filter, narrowing the already-filtered pool."
        ),
    ),
    filter_mode: FilterMode = typer.Option(
        DEFAULT_FILTER_MODE,
        "--filter-mode",
        help=(
            "Matching mode for filtering query with [yellow]EXACT[/yellow] for case-insensitive whole-field"
            " equality; [yellow]CONTAINS[/yellow] for case-insensitive substring;"
            " [yellow]FUZZY[/yellow] for splitting query into words, each"
            " matches as subsequence or by edit-distance"
            " closeness, all words required."
        ),
        show_default=True,
    ),
    filter_by: FilterBy = typer.Option(
        DEFAULT_FILTER_BY,
        "--filter-by",
        help=(
            "Field to match the filter query against. [yellow]DESCRIPTION[/yellow]"
            " filters on check description; [yellow]NAME[/yellow] filters on"
            " check name or, as a fallback, check command;"
            " [yellow]HINT[/yellow] filters on check's hint; [yellow]ANY[/yellow]"
            " filters across all three fields."
        ),
        show_default=True,
    ),
    filter_type: FilterType = typer.Option(
        DEFAULT_FILTER_TYPE,
        "--filter-type",
        help=(
            "Whether to [yellow]INCLUDE[/yellow] (i.e., keep) or [yellow]EXCLUDE[/yellow] (i.e., drop) the checks"
            " that match the filter's criteria."
        ),
        show_default=True,
    ),
    filter_fuzzy_threshold: float = typer.Option(
        DEFAULT_FILTER_FUZZY_THRESHOLD,
        "--filter-fuzzy-threshold",
        help=(
            "Threshold for fuzzy word matching (0.0 to 1.0). Higher"
            " values result in less stringent (i.e., more fuzzy) matching."
            " Requires --filter-mode [yellow]FUZZY[/yellow]."
        ),
        show_default=True,
        callback=validate_filter_fuzzy_threshold,
    ),
    filter_failed_last: Optional[int] = typer.Option(
        None,
        "--filter-failed-last",
        help=(
            "Only run checks that failed in at least the specified number of the most recent"
            " reports. This status filter runs first, before any --filter-query text"
            " filter, which then narrows the already-reduced pool."
        ),
        show_default=True,
        callback=validate_filter_failed_last,
    ),
    filter_passed_last: Optional[int] = typer.Option(
        None,
        "--filter-passed-last",
        help=(
            "Only run checks that passed in all of the specified number"
            " of the most recent reports. This status filter runs first,"
            " before any --filter-query text filter. When combined with"
            " --filter-failed-last, the two status filters intersect"
            " their matching checks before any text filter runs."
        ),
        show_default=True,
        callback=validate_filter_passed_last,
    ),
    report_history: bool = typer.Option(
        True,
        "--report-history/--no-report-history",
        help=(
            "Save bounded amount of JSON report history in the user data directory"
            f" ({DEFAULT_REPORT_HISTORY_DIR})."
        ),
    ),
    report_history_max_count: int = typer.Option(
        DEFAULT_HISTORY_REPORT_COUNT,
        "--report-history-max-count",
        help="Maximum number of automatic JSON reports to retain.",
        show_default=True,
        callback=validate_report_history_count,
    ),
    report_history_max_mib: int = typer.Option(
        DEFAULT_HISTORY_SIZE_MIB,
        "--report-history-max-mb",
        help="Maximum total size of automatic reports in MiB.",
        show_default=True,
        callback=validate_report_history_size,
    ),
    report: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--report",
        "-r",
        help=(
            "A tuple containing the following required values:"
            " 1. The destination of the report (either [blue]FILE[/blue] or [blue]ENV[/blue]);"
            " 2. The format of the report (either [blue]JSON[/blue] or [blue]MD[/blue]);"
            " 3. The name of the file or environment variable;"
            " (Use [blue]ENV MD GITHUB_STEP_SUMMARY[/blue] to make summary in GitHub Actions or"
            " [blue]FILE JSON report.json[/blue] to save summary in [blue]report.json[/blue])."
        ),
        callback=validate_report,
    ),
    github_env: Tuple[str, str] = typer.Option(
        (None, None),
        "--github-env",
        "-g",
        help=(
            "A tuple containing the following required values:"
            " 1. The format of the data (either [blue]JSON[/blue] or [blue]MD[/blue]);"
            " 2. The name of the environment variable to set;"
            " (Use [blue]json JSON_REPORT[/blue] to store [blue]JSON[/blue] data or"
            " [blue]md MD_REPORT[/blue] to store Markdown data in the"
            " GITHUB_ENV file for downstream steps)."
        ),
        callback=validate_github_env,
    ),
    output_limit: int = typer.Option(
        5,
        "--output-limit",
        "-o",
        help="Maximum number of diagnostic lines to display for a check (>= 1).",
        callback=validate_output_limit,
    ),
    baseline_weight: int = typer.Option(
        1,
        "--baseline-weight",
        "-b",
        help="Default weight applied to checks without an explicit weight (>= 1).",
        callback=validate_baseline_weight,
    ),
    progress_bar: bool = typer.Option(
        True,
        "--progress-bar/--no-progress-bar",
        help="Show or hide the progress bar for checks.",
    ),
    verbose: bool = typer.Option(
        False,
        "--verbose/--no-verbose",
        help="Show detailed configuration info before running checks.",
    ),
    show_diagnostics: bool = typer.Option(
        True,
        "--show-diagnostics/--no-show-diagnostics",
        help="Show or hide diagnostic details for failing checks.",
    ),
    auto_hint: bool = typer.Option(
        False,
        "--auto-hint/--no-auto-hint",
        help="Automatically generate hints for failing checks.",
    ),
    auto_hint_track: bool = typer.Option(
        True,
        "--auto-hint-track/--no-auto-hint-track",
        help=(
            "Save auto-hint generation details to autohints.json "
            "in the current working directory (only when "
            "--auto-hint is enabled and hints are generated)."
        ),
    ),
    auto_hint_model: str = typer.Option(
        AUTO_HINT_MODEL_DEFAULT,
        "--auto-hint-model",
        help=(
            "Model for auto-hint generation "
            "(requires --auto-hint). Defaults to"
            f" [blue]{REMOTE_MODEL_DEFAULT}[/blue] when --auto-hint-url is set"
            f" or [blue]{DEFAULT_MODEL_ID}[/blue] otherwise."
        ),
        show_default=False,
    ),
    auto_hint_url: Optional[str] = typer.Option(
        None,
        "--auto-hint-url",
        help=(
            "URL of an OpenAI-compatible API server for remote hint "
            "generation (requires --auto-hint). When provided, the "
            "remote model is used instead of a local model. Falls "
            "back to default local model on any remote URL errors."
        ),
    ),
    auto_hint_api_key: Optional[str] = typer.Option(
        None,
        "--auto-hint-api-key",
        help=(
            "API key for the remote auto-hint server "
            "(requires --auto-hint-url)."
        ),
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help=(
            "Exit after showing the GatorGrade version and other details "
            "(e.g., active versions of Python, GatorGrader, and operating system)."
        ),
    ),
) -> None:
    """Run the GatorGrader checks in the specified configuration file."""
    # resolve the config directory and configuration file path;
    # the precedence for looking for the gatorgrade.yml file is:
    # 1. the specified filename in the current working directory;
    # 2. the specified filename inside the --config-dir directory
    #    (either the user-specified value for this directory
    #    or the default platformdirs config directory);
    # 3. if the file is not found in either location, the filename
    #    itself is returned so that the downstream code can report
    #    a clear "file not found" error for that specified file
    resolved_config_dir: Path | None = config_dir
    resolved_filename = resolve_config_path(filename, resolved_config_dir)
    # if ctx.subcommand is None then this means
    # that, by default, gatorgrade should run in checking mode;
    # note that the current implementation of the tool only
    # supports checking mode as all others are deprecated;
    # also note that the output of the tool is now segmented
    # into sections that are demarcated by horizintal rules
    if ctx.invoked_subcommand is None:
        # check the due date before parsing config so warnings appear before setup;
        # this returns both the due date and any errors that might have arisen
        # when parsing the due date (i.e., due to an incorrect time/date format)
        due_date, due_date_error = get_due_date(resolved_filename)
        if has_due_date_field(resolved_filename) and due_date is None:
            console.print()
            console.print(
                Rule(
                    Text("Invalid Due Date Configuration"),
                    style="bright_yellow",
                )
            )
            console.print()
            # display the specific due date parsing error
            if due_date_error:
                console.print(due_date_error)
            # if there is some other type of error, then
            # display a generic message about due date parsing
            else:
                console.print(
                    "Ignoring the due date in the configuration file "
                    "as it could not be parsed."
                )
            # display a message about the required format for the
            # due date as a reminder (note that this is the type of
            # message that would prove most helpful to instructors
            # who are creating an assignment and not to students)
            console.print(
                "Expected an ISO 8601 format such as '2026-12-15' "
                "or '2026-12-15T23:59:00'."
            )
            console.print()
            console.print(Rule(style="bright_yellow"))
        # warn if multiple due date aliases are present
        # (there are multiple ways to specify a due date,
        # in terms of the keys that are accepted in the front
        # matter, include both "due_date" and "duedate")
        aliases_present = get_due_date_aliases_present(resolved_filename)
        if len(aliases_present) > 1:
            chosen = aliases_present[0]
            ignored = ", ".join(aliases_present[1:])
            console.print()
            console.print(
                Rule(
                    Text("Multiple Due Date Fields"),
                    style="bright_yellow",
                )
            )
            console.print()
            console.print(
                f"Multiple due date fields found: "
                f"{', '.join(aliases_present)}."
            )
            console.print(f"Using '{chosen}' and ignoring {ignored}.")
            console.print("Use only one due date field.")
            console.print()
            console.print(Rule(style="bright_yellow"))
        # show verbose configuration information if requested
        _print_verbose_info(
            verbose,
            resolved_filename,
            resolved_config_dir or get_config_dir(),
            auto_hint,
            auto_hint_model,
            auto_hint_url,
            output_limit,
            baseline_weight,
            show_diagnostics,
            progress_bar,
            auto_hint_track=auto_hint_track,
            filter_query=filter_query,
            filter_mode=filter_mode,
            filter_by=filter_by,
            filter_type=filter_type,
            filter_fuzzy_threshold=filter_fuzzy_threshold,
            filter_failed_last=filter_failed_last,
            filter_passed_last=filter_passed_last,
            report_history=report_history,
            report_history_max_count=report_history_max_count,
            report_history_max_mib=report_history_max_mib,
        )
        # parse the provided configuration file
        checks, parse_error = parse_config(resolved_filename, baseline_weight)
        # extract the optional project name from the config file
        project_name = get_project_name(resolved_filename)
        history_scope = get_history_scope(resolved_filename, project_name)
        # determine whether any pre-run filter was provided
        filter_was_active = (
            bool(filter_query)
            or filter_failed_last is not None
            or filter_passed_last is not None
        )
        history_reports_inspected = 0
        history_reports_total = 0
        # validate filter option combinations;
        # this catches:
        #   --filter-mode/--filter-by/--filter-type without
        #     --filter-query
        #   --filter-query with empty or whitespace-only string
        #   --filter-fuzzy-threshold without --filter-mode FUZZY
        # happens before config parsing so errors are independent
        # of whether the config file exists or is valid
        filter_errors = validate_filter_options(
            filter_query,
            filter_mode,
            filter_by,
            filter_type,
            filter_fuzzy_threshold=filter_fuzzy_threshold,
        )
        if filter_errors:
            checks_status = False
            console.print()
            console.print(
                Rule(
                    CONFIG_ERROR_LABEL,
                    style="bright_red",
                )
            )
            if filter_errors:
                console.print()
            for error in filter_errors:
                console.print(error)
            console.print(Text(EXIT_MESSAGE))
            console.print()
            console.print(Rule(style="bright_red"))
            sys.exit(FAILURE)
        # validate auto-hint option combinations;
        # this catches:
        #   --auto-hint-model without --auto-hint
        #   --auto-hint-url without --auto-hint
        #   --auto-hint-api-key without --auto-hint-url
        auto_hint_errors = validate_auto_hint_options(
            auto_hint,
            auto_hint_model,
            auto_hint_url,
            auto_hint_api_key,
        )
        if auto_hint_errors:
            checks_status = False
            console.print()
            console.print(
                Rule(
                    CONFIG_ERROR_LABEL,
                    style="bright_red",
                )
            )
            # display a blank line if there is
            # at least one error in configuration
            # for the auto-hinting feature
            if auto_hint_errors:
                console.print()
            # display the errors in configuration
            # for the auto-hinting (note that there
            # could be one or more errors)
            for error in auto_hint_errors:
                console.print(error)
            console.print(Text(EXIT_MESSAGE))
            console.print()
            console.print(Rule(style="bright_red"))
            sys.exit(FAILURE)
        # a YAML parsing error occurred and thus the
        # tool should display the error and exit
        if parse_error is not None:
            checks_status = False
            console.print()
            console.print(
                Rule(Text(CONFIG_ERROR_PLURAL_LABEL), style="bright_red")
            )
            console.print(NEWLINE + parse_error)
            console.print(Text(EXIT_MESSAGE))
            console.print()
            console.print(Rule(style="bright_red"))
        # there are valid checks and thus the
        # tool should run them with run_checks
        elif len(checks) > 0:
            # capture the original check count before filtering
            pre_filter_count = len(checks)
            # resolve filter defaults when filter_query is active
            # (must happen before cli_args dict references them)
            resolved_filter_mode = (
                filter_mode if filter_mode is not None else DEFAULT_FILTER_MODE
            )
            resolved_filter_by = (
                filter_by if filter_by is not None else DEFAULT_FILTER_BY
            )
            resolved_filter_type = (
                filter_type if filter_type is not None else DEFAULT_FILTER_TYPE
            )
            # create a dictionary of the CLI arguments to pass to the report
            # (this will enable them to be saved inside of a report)
            cli_args = {
                CONFIG_FLAG: str(resolved_filename),
                CONFIG_DIR_FLAG: str(resolved_config_dir)
                if resolved_config_dir
                else None,
                REPORT_FLAG: list(report),
                GITHUB_ENV_FLAG: list(github_env),
                OUTPUT_LIMIT_FLAG: output_limit,
                BASELINE_WEIGHT_FLAG: baseline_weight,
                VERBOSE_FLAG: verbose,
                PROGRESS_BAR_FLAG: progress_bar,
                SHOW_DIAGNOSTICS_FLAG: show_diagnostics,
                AUTO_HINT_FLAG: auto_hint,
                AUTO_HINT_MODEL_FLAG: auto_hint_model
                if auto_hint_model
                else None,
                AUTO_HINT_URL_FLAG: str(auto_hint_url)
                if auto_hint_url
                else None,
                AUTO_HINT_API_KEY_FLAG: str(auto_hint_api_key)
                if auto_hint_api_key
                else None,
                AUTO_HINT_TRACK_FLAG: auto_hint_track,
                FILTER_QUERY_FLAG: filter_query,
                FILTER_MODE_FLAG: resolved_filter_mode.value
                if filter_was_active
                else None,
                FILTER_BY_FLAG: resolved_filter_by.value
                if filter_was_active
                else None,
                FILTER_TYPE_FLAG: resolved_filter_type.value
                if filter_was_active
                else None,
                FILTER_TOTAL_FLAG: pre_filter_count
                if filter_was_active
                else None,
                FILTER_FUZZY_THRESHOLD_FLAG: filter_fuzzy_threshold
                if filter_was_active
                and resolved_filter_mode == FilterMode.FUZZY
                else None,
                FILTER_FAILED_LAST_FLAG: filter_failed_last,
                FILTER_PASSED_LAST_FLAG: filter_passed_last,
                FILTER_HISTORY_REPORTS_FLAG: history_reports_inspected,
                FILTER_HISTORY_REPORTS_TOTAL_FLAG: history_reports_total,
                REPORT_HISTORY_FLAG: report_history,
                REPORT_HISTORY_MAX_COUNT_FLAG: report_history_max_count,
                REPORT_HISTORY_MAX_MIB_FLAG: report_history_max_mib,
            }
            version_info = {
                GATORGRADE_VERSION_KEY: GATORGRADE_VERSION,
                GATORGRADER_VERSION_KEY: importlib.metadata.version(
                    GATORGRADER_DEPENDENCY
                ),
                PYTHON_INFO_KEY: get_python_info(),
                PLATFORM_INFO_KEY: get_platform_info(),
                OS_RELEASE_KEY: get_os_release(),
            }
            # at the outset, there is no auto-hinting engine
            # unless the person using gatorgrade has explicitly
            # opted in to using auto-hinting both through the
            # command line and through running the tool with
            # the optional dependencies installed (auto-hinting
            # relies on local transformers or, if specified,
            # a remote OpenAI-compatible API, both of which we
            # do not want to load unless the opt-in was made)
            auto_hint_engine = None
            # apply historical filtering before text filtering
            # supports --filter-failed-last, --filter-passed-last, and
            # their combination (intersection of matching checks)
            if (
                filter_failed_last is not None
                or filter_passed_last is not None
            ):
                try:
                    historical_check_ids: set[str] | None = None
                    # get the failed check IDs
                    if filter_failed_last is not None:
                        (
                            failed_ids,
                            failed_inspected,
                            history_reports_total,
                        ) = get_failed_check_ids(
                            get_report_history_directory(),
                            history_scope,
                            filter_failed_last,
                        )
                        history_reports_inspected = failed_inspected
                        historical_check_ids = failed_ids
                    # get the passed check IDs by extracting
                    # all of the checks from the history and then
                    # using the information about the failed checks
                    # to indirectly determine which checks passed
                    if filter_passed_last is not None:
                        reports_dir = get_report_history_directory()
                        all_ids = get_all_check_ids(
                            reports_dir,
                            history_scope,
                            filter_passed_last,
                        )
                        (
                            passed_failed_ids,
                            passed_inspected,
                            passed_total_reports,
                        ) = get_failed_check_ids(
                            reports_dir,
                            history_scope,
                            filter_passed_last,
                        )
                        passed_ids = all_ids - passed_failed_ids
                        if historical_check_ids is not None:
                            historical_check_ids &= passed_ids
                        else:
                            historical_check_ids = passed_ids
                        # use the larger inspection count for display
                        history_reports_inspected = max(
                            history_reports_inspected, passed_inspected
                        )
                        # set total when there is no failed-last path
                        if history_reports_total == 0:
                            history_reports_total = passed_total_reports
                except (OSError, TypeError, ValueError) as error:
                    console.print(
                        "[yellow]Warning: Could not read report history. "
                        f"Running all checks instead: {error}[/]"
                    )
                else:
                    # there were historical check IDs found
                    # and thus we can filter the checks
                    if (
                        historical_check_ids is not None
                        and len(historical_check_ids) > 0
                    ):
                        checks = filter_checks_by_failed_ids(
                            checks,
                            historical_check_ids,
                        )
                    # there were no historical check IDs found and thus
                    # it is important to specify an empty list which
                    # means that there are not checks to run and there
                    # should be a warning message displayed to the user
                    elif historical_check_ids is not None:
                        checks = []
            # update the filter-total counts to reflect the
            # check pool AFTER historical (status) filtering,
            # which is exactly what the text filter below will
            # operate on. Without this update, the "Selected
            # from N checks" display would still report the
            # original pre-filter count and overstate the pool.
            # this matters when historical filtering runs first
            # and narrows the check list before text filtering.
            cli_args[FILTER_TOTAL_FLAG] = (
                len(checks) if filter_was_active else None
            )
            # apply text filtering after historical filtering
            if filter_query:
                checks = filter_checks(
                    checks,
                    mode=resolved_filter_mode,
                    by=resolved_filter_by,
                    ftype=resolved_filter_type,
                    query=filter_query,
                    fuzzy_threshold=filter_fuzzy_threshold,
                )
            cli_args[FILTER_HISTORY_REPORTS_FLAG] = history_reports_inspected
            cli_args[FILTER_HISTORY_REPORTS_TOTAL_FLAG] = history_reports_total
            # if filtering emptied the list, handle it here before
            # auto-hint engine and run_checks are reached
            if filter_was_active and not checks:
                checks_status = True
                console.print()
                console.print(Rule("Filter Results", style="green"))
                console.print()
                console.print("No checks matched the filter; nothing to run.")
                console.print()
                console.print(Rule(style="green"))
            else:
                # auto-hint engine: try to create it if --auto-hint is passed;
                # the engine sources hints from a remote OpenAI-compatible API
                # (i.e., when --auto-hint-url is provided) or from a local
                # huggingface transformers model (i.e., when no URL is provided).
                # remote engine fails to initialise or returns None for a hint,
                # the program falls back to the local engine; resolve the system prompt
                # and validation rules if specified in the config front matter
                if auto_hint:
                    system_prompt = resolve_system_prompt(
                        resolved_filename, resolved_config_dir
                    )
                    validation_rules = resolve_validation_rules(
                        resolved_filename, resolved_config_dir
                    )
                    auto_hint_engine = create_auto_hint_engine(
                        resolved_filename,
                        auto_hint_model,
                        auto_hint_url,
                        auto_hint_api_key,
                        system_prompt=system_prompt,
                        validation_rules=validation_rules,
                        auto_hint_model_default=AUTO_HINT_MODEL_DEFAULT,
                        console=console,
                    )
                # run the checks that were specified in a way
                # that adheres to the configuration both in
                # the command-line arguments and also in the
                # gatorgrade.yml file
                checks_status = run_checks(
                    checks,
                    report,
                    not progress_bar,
                    show_diagnostics,
                    output_limit,
                    cli_args,
                    version_info,
                    github_env,
                    project_name,
                    due_date,
                    auto_hint_engine=auto_hint_engine,
                    auto_hint_url=auto_hint_url,
                    auto_hint_track=auto_hint_track,
                    report_history=report_history,
                    report_history_max_count=report_history_max_count,
                    report_history_max_mib=report_history_max_mib,
                    history_scope=history_scope,
                )
        # no checks were created and this means
        # that, most likely, the file was not
        # valid and thus the tool cannot run checks
        else:
            checks_status = False
            console.print()
            console.print(Rule(CONFIG_ERROR_LABEL, style="bright_red"))
            console.print()
            console.print(
                f"The path {resolved_filename} either does not exist or is not valid."
            )
            console.print(Text(EXIT_MESSAGE))
            console.print()
            console.print(Rule(style="bright_red"))
        # at least one of the checks did not pass or
        # the provided file was not valid and thus
        # the tool should return a non-zero exit
        # code to designate some type of failure
        if checks_status is not True:
            sys.exit(FAILURE)


def _echo_insights(payload: str) -> None:
    """Display insights with colored text headings and unchanged JSON."""
    # markup, emoji, and highlighting are disabled so that punctuation
    # inside a check description is never reinterpreted, and soft
    # wrapping is enabled so that terminal width cannot fold a long
    # line and invalidate the JSON that was requested
    display = Text(payload.rstrip(NEWLINE))
    if not payload.lstrip().startswith(INSIGHTS_JSON_START):
        heading = NEWLINE.join(payload.splitlines()[:INSIGHTS_HEADING_LINES])
        display.stylize(INSIGHTS_HEADING_STYLE, end=len(heading))
        # locate each highlighted word inside the heading itself so that
        # the styling keeps working if the title text is ever reworded
        for word, style in INSIGHTS_TITLE_STYLES:
            start = heading.find(word)
            if start >= 0:
                display.stylize(style, start=start, end=start + len(word))
        for pattern, style in INSIGHTS_TABLE_STYLES:
            display.highlight_regex(pattern, style=style)
    console.print(
        display,
        markup=False,
        emoji=False,
        highlight=False,
        soft_wrap=True,
    )


def _resolve_insights_config(
    config: Path,
    config_dir: Optional[Path],
) -> Path:
    """Return the resolved configuration path or exit when it is missing."""
    resolved_config = resolve_config_path(config, config_dir)
    if not resolved_config.is_file():
        console.print()
        console.print(Rule(CONFIG_ERROR_LABEL, style="bright_red"))
        console.print()
        console.print(INSIGHTS_CONFIG_MISSING_FMT.format(resolved_config))
        console.print()
        console.print(Rule(style="bright_red"))
        raise typer.Exit(FAILURE)
    return resolved_config


def _write_insights_file(
    output_file: Path,
    contents: str,
    output_format: InsightsFormat,
) -> None:
    """Write rendered insights to a file and confirm on the terminal."""
    try:
        # create the containing directory on demand so that a saved report
        # can land in a conventional folder that is not committed yet
        output_file.parent.mkdir(parents=True, exist_ok=True)
        output_file.write_text(contents, encoding=INSIGHTS_FILE_ENCODING)
    except OSError as error:
        console.print(
            INSIGHTS_WRITE_ERROR_FMT.format(output_file, error),
            style="bright_red",
        )
        raise typer.Exit(FAILURE) from error
    console.print(
        INSIGHTS_WROTE_FMT.format(output_format.value, output_file),
        style="green",
    )


def _load_insights_report(input_file: Path) -> InsightsReport:
    """Load a previously saved insights report or exit when it is invalid."""
    try:
        contents = input_file.read_text(encoding=INSIGHTS_FILE_ENCODING)
    except (OSError, UnicodeDecodeError) as error:
        console.print(
            INSIGHTS_READ_ERROR_FMT.format(input_file, error),
            style="bright_red",
        )
        raise typer.Exit(FAILURE) from error
    # a saved report is validated through the same model that produced it,
    # so unparsable JSON, a missing field, and a field of the wrong type are
    # all rejected here rather than surfacing later as a confusing traceback
    try:
        return InsightsReport.model_validate_json(contents)
    except ValidationError as error:
        console.print(
            INSIGHTS_INVALID_FMT.format(input_file),
            style="bright_red",
        )
        raise typer.Exit(FAILURE) from error


def _insights_destination(
    output_file: Optional[Path],
    save: bool,
    output_format: InsightsFormat,
) -> Optional[Path]:
    """Return where a report should be written, or None to only display it."""
    if output_file is not None:
        return output_file
    if save:
        return INSIGHTS_SAVE_DIRECTORY / INSIGHTS_SAVE_NAMES[output_format]
    return None


def _reject_insights_conflict(first: str, second: str) -> None:
    """Exit because two options that both choose a destination were given."""
    console.print()
    console.print(Rule(CONFIG_ERROR_LABEL, style="bright_red"))
    console.print()
    console.print(INSIGHTS_SAVE_CONFLICT_FMT.format(first, second))
    console.print()
    console.print(Rule(style="bright_red"))
    raise typer.Exit(FAILURE)


def _reject_insights_input_conflicts(ctx: typer.Context) -> None:
    """Exit when history options accompany a saved report to analyze."""
    conflicting = [
        flag
        for parameter, flag in (
            (INSIGHTS_LAST_PARAMETER, INSIGHTS_LAST_FLAG),
            (INSIGHTS_HISTORY_DIR_PARAMETER, INSIGHTS_HISTORY_DIR_FLAG),
        )
        if ctx.get_parameter_source(parameter) == ParameterSource.COMMANDLINE
    ]
    if not conflicting:
        return
    console.print()
    console.print(Rule(CONFIG_ERROR_LABEL, style="bright_red"))
    console.print()
    console.print(
        INSIGHTS_INPUT_CONFLICT_FMT.format(
            INSIGHTS_INPUT_FLAG,
            INSIGHTS_CONFLICT_SEPARATOR.join(conflicting),
        )
    )
    console.print()
    console.print(Rule(style="bright_red"))
    raise typer.Exit(FAILURE)


def _build_history_insights(
    config: Path,
    config_dir: Optional[Path],
    last: int,
    history_dir: Path,
) -> InsightsReport:
    """Analyze saved report history without running any checks."""
    resolved_config = _resolve_insights_config(config, config_dir)
    history_scope = get_history_scope(
        resolved_config,
        get_project_name(resolved_config),
    )
    # load the whole in-scope history a single time and then slice it;
    # asking the loader for a capped set and then asking again for the
    # total would read and parse every history file twice per run
    payloads, file_diagnostics = load_history_reports_with_diagnostics(
        history_dir,
        history_scope,
    )
    return build_insights_report(
        payloads[:last],
        reports_available=len(payloads),
        scope=history_scope,
        file_diagnostics=file_diagnostics,
    )


def _run_insights(  # noqa: PLR0913
    ctx: typer.Context,
    config: Path,
    config_dir: Optional[Path],
    last: int,
    output_format: InsightsFormat,
    output_file: Optional[Path],
    history_dir: Path,
    instructor: bool,
    input_file: Optional[Path],
    save: bool,
) -> None:
    """Render insights from a saved report or from saved report history."""
    if save and output_file is not None:
        _reject_insights_conflict(INSIGHTS_SAVE_FLAG, INSIGHTS_OUTPUT_FLAG)
    destination = _insights_destination(
        output_file,
        save,
        output_format,
    )
    if input_file is not None:
        _reject_insights_input_conflicts(ctx)
        report = _load_insights_report(input_file)
    else:
        report = _build_history_insights(
            config,
            config_dir,
            last,
            history_dir,
        )
    text_view = render_text(report, instructor=instructor)
    selected_view = (
        render_json(report)
        if output_format is InsightsFormat.JSON
        else text_view
    )
    if destination is None:
        _echo_insights(selected_view)
        return
    # show the readable summary first so that the confirmation of the
    # written file remains the final line displayed in the terminal
    _echo_insights(text_view)
    _write_insights_file(
        destination,
        selected_view.rstrip(NEWLINE) + NEWLINE,
        output_format,
    )


def _insights_entry(  # noqa: PLR0913
    ctx: typer.Context,
    config: Path = typer.Option(
        FILE,
        "--config",
        "-c",
        help="Name of the configuration file in YML format.",
    ),
    config_dir: Optional[Path] = typer.Option(
        None,
        "--config-dir",
        "-d",
        help=(
            "Directory for the configuration file that identifies"
            " which project's report history to analyze."
        ),
        show_default=DEFAULT_CONFIG_DIR,
    ),
    last: int = typer.Option(
        INSIGHTS_DEFAULT_LAST,
        INSIGHTS_LAST_FLAG,
        "-l",
        help="Number of the most recent reports to analyze (>= 1).",
        show_default=True,
        callback=validate_insights_last,
    ),
    output_format: InsightsFormat = typer.Option(
        InsightsFormat.TEXT,
        "--format",
        "-f",
        help=(
            "Output format with [blue]text[/blue] for a readable summary"
            " or [blue]json[/blue] for machine-readable results."
        ),
        show_default=True,
    ),
    output_file: Optional[Path] = typer.Option(
        None,
        INSIGHTS_OUTPUT_FLAG,
        "-o",
        help=(
            "Write the analysis in the chosen format to this file, creating"
            " any missing directories; the terminal still displays the"
            " readable text summary."
        ),
        callback=validate_insights_output,
    ),
    save: bool = typer.Option(
        False,
        INSIGHTS_SAVE_FLAG,
        "-s",
        help=(
            "Save the analysis into the insights directory, creating it"
            " when needed, so the report stays at the path checks expect."
        ),
    ),
    history_dir: Path = typer.Option(
        get_report_history_directory(),
        INSIGHTS_HISTORY_DIR_FLAG,
        help="Directory that holds the saved JSON report history.",
        show_default=DEFAULT_REPORT_HISTORY_DIR,
    ),
    instructor: bool = typer.Option(
        False,
        "--instructor/--no-instructor",
        help=(
            "Add the detail that is useful to an instructor, such as check"
            " identifiers, trend values, and every skipped history file."
        ),
    ),
    input_file: Optional[Path] = typer.Option(
        None,
        INSIGHTS_INPUT_FLAG,
        "-i",
        help=(
            "Analyze a previously saved JSON report instead of the report"
            " history; cannot be combined with --last or --history-dir."
        ),
        callback=validate_insights_input,
    ),
) -> None:
    """Analyze report history for pass rates, streaks, and check trends."""
    _run_insights(
        ctx,
        config,
        config_dir,
        last,
        output_format,
        output_file,
        history_dir,
        instructor,
        input_file,
        save,
    )


# register the same analysis entry point under two names so that the
# feature is discoverable as either gatorgrade insights or as the
# gatorgrade analyze alias; the alias overrides the shared docstring so
# that the help menu shows the two names as one command and not as two
# unrelated commands that happen to behave the same way
app.command(INSIGHTS_COMMAND_NAME)(_insights_entry)
app.command(ANALYZE_COMMAND_NAME, help=ANALYZE_HELP)(_insights_entry)


if __name__ == "__main__":
    app()
