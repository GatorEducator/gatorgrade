"""Use GatorGrade to run checks and generate helpful output."""

import importlib.metadata
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

import typer
from rich.console import Console
from rich.emoji import Emoji
from rich.rule import Rule
from rich.text import Text

from gatorgrade.detect import (
    GATORGRADER_DEPENDENCY,
    _get_os_release,
    _get_platform_info,
    _get_python_info,
    _print_version_info,
)
from gatorgrade.hint.fallback import (
    FallbackHintEngine,
    RemoteEngineAdapter,
)
from gatorgrade.hint.local_engine import (
    DEFAULT_MODEL_ID,
    AutoHintEngine,
)
from gatorgrade.hint.remote_engine import (
    REMOTE_API_KEY_DEFAULT,
    REMOTE_MODEL_DEFAULT,
    RemoteHintEngine,
)
from gatorgrade.input.parse_config import (
    get_auto_hint_model,
    get_config_dir,
    get_due_date,
    get_due_date_aliases_present,
    get_project_name,
    get_system_prompt_file,
    get_validation_phrases_file,
    has_due_date_field,
    parse_config,
    resolve_config_path,
)
from gatorgrade.output.output import run_checks
from gatorgrade.validate import (
    _validate_baseline_weight,
    _validate_github_env,
    _validate_output_limit,
    _validate_report,
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

# create a Typer app that
# --> does not support completion
# --> has a specified help message with an emoji
app = typer.Typer(
    add_completion=False,
    help=f"{gatorgrade_emoji} Run the GatorGrader checks in the specified configuration file.",
)

# create a default console for printing with rich
console = Console()

# define constants used in this module
FILE = "gatorgrade.yml"
FAILURE = 1

# newline character for joining lines
NEWLINE = "\n"

# exit message
EXIT_MESSAGE = "Fix these error(s) before running gatorgrade."

# default config directory computed at module load time for display in help
DEFAULT_CONFIG_DIR = str(get_config_dir())

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
AUTO_HINT_MODEL_DEFAULT = (
    "__default_model__"  # sentinel to detect if flag was explicitly passed
)
AUTO_HINT_URL_FLAG = "--auto-hint-url"
AUTO_HINT_API_KEY_FLAG = "--auto-hint-api-key"
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


def _version_callback(value: bool) -> None:
    """Print the GatorGrade version and exit when --version is provided."""
    if value:
        _print_version_info(console)
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

    """
    if not verbose:
        return
    console.print()
    console.print(Rule("Verbose Mode Information", style="green"))
    console.print()
    _print_version_info(console)
    console.print(f"Config file: {config_path}")
    console.print(f"Config dir:  {config_dir}")
    console.print(f"Output limit:  {output_limit}")
    console.print(f"Baseline weight: {baseline_weight}")
    console.print(f"Diagnostics: {show_diagnostics}")
    console.print(f"Progress:    {progress_bar}")
    console.print(f"Auto-hint:   {auto_hint}")
    if auto_hint:
        model_display = auto_hint_model
        if auto_hint_model == AUTO_HINT_MODEL_DEFAULT:
            model_display = (
                REMOTE_MODEL_DEFAULT if auto_hint_url else DEFAULT_MODEL_ID
            )
        console.print(f"Model:       {model_display}")
        if auto_hint_url:
            console.print(f"Remote URL:  {auto_hint_url}")
    console.print()
    console.print(Rule(style="green"))


def _resolve_system_prompt(
    config_path: Path, config_dir: Optional[Path]
) -> Optional[str]:
    """Read the system prompt file if specified in the config front matter.

    The filename is read from the system_prompt_file field in
    the YAML front matter, then resolved in this search order:

    1. Current working directory
    2. Alongside the configuration file itself
    3. The --config-dir directory (or the default platformdirs-
       based config directory)

    Args:
        config_path: Path to the resolved gatorgrade configuration
            file.
        config_dir: The config directory (from --config-dir),
            or None to use the default.

    Returns:
        The contents of the system prompt file, or None if not
        specified or not found.

    """
    prompt_filename = get_system_prompt_file(config_path)
    if not prompt_filename:
        return None
    # search order: cwd, alongside config file, config dir
    for candidate in [
        Path(prompt_filename),
        config_path.parent / prompt_filename,
        (config_dir or get_config_dir()) / prompt_filename,
    ]:
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError:
                return None
    return None


def _resolve_validation_rules(
    config_path: Path, config_dir: Optional[Path]
) -> dict[str, list[str]] | None:
    """Read the validation rules JSON file if specified in the config front matter.

    The filename is read from the validation_phrases_file field
    in the YAML front matter. The JSON file must contain an object
    with optional keys:

    - must_contain: list of phrases that must appear in hints
    - cannot_contain: list of phrases that must not appear

    The file is resolved in the same search order as the system
    prompt: CWD, alongside config file, then config dir.

    Args:
        config_path: Path to the resolved gatorgrade configuration
            file.
        config_dir: The config directory (from --config-dir),
            or None to use the default.

    Returns:
        The parsed validation rules dict, or None if not specified
        or not found.

    """
    import json  # noqa: PLC0415

    filename = get_validation_phrases_file(config_path)
    if not filename:
        return None
    for candidate in [
        Path(filename),
        config_path.parent / filename,
        (config_dir or get_config_dir()) / filename,
    ]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    return None
                return data
            except (json.JSONDecodeError, OSError):
                return None
    return None


def _create_auto_hint_engine(  # noqa: PLR0913
    filename: Path,
    auto_hint_model: str,
    auto_hint_url: Optional[str],
    auto_hint_api_key: Optional[str],
    system_prompt: str | None = None,
    validation_rules: dict[str, list[str]] | None = None,
) -> Any:
    """Create the appropriate auto-hint engine based on CLI arguments.

    When --auto-hint-url is provided, a RemoteHintEngine is
    attempted first. If it succeeds, it is returned. If it
    fails (e.g. the URL is unreachable or pydantic_ai is not
    installed), a warning is printed and the engine falls back
    to a local AutoHintEngine.

    When no URL is provided, a local AutoHintEngine is created
    directly, using the default configuration for auto-hinting.

    Args:
        filename: Path to the config file (for reading
            auto_hint_model from front matter).
        auto_hint_model: Model ID from the CLI, or a sentinel
            default value.
        auto_hint_url: URL of the remote API server, or None.
        auto_hint_api_key: API key for the remote server.
        system_prompt: Optional custom system prompt.
            If provided, this replaces the built-in default.
        validation_rules: Optional dict with must_contain
            and/or cannot_contain lists of phrases to
            check, in addition to the built-in quality rules.

    Returns:
        An AutoHintEngine instance, or None if creation fails.

    """
    # resolve the model ID from the CLI, config file, or default;
    # the remote engine has its own default model, separate from
    # the local engine default
    model_id = auto_hint_model
    remote_model_id = auto_hint_model
    if (
        not model_id
        or not model_id.strip()
        or model_id == AUTO_HINT_MODEL_DEFAULT
    ):
        config_model = get_auto_hint_model(filename)
        model_id = config_model or DEFAULT_MODEL_ID
        remote_model_id = config_model or REMOTE_MODEL_DEFAULT
    # build the primary and fallback local engines
    primary_local_model = DEFAULT_MODEL_ID if auto_hint_url else model_id
    fallback_local_model = DEFAULT_MODEL_ID
    try:
        primary_engine = AutoHintEngine(
            model_id=primary_local_model,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
    except Exception:
        primary_engine = None
    try:
        fallback_engine = AutoHintEngine(
            model_id=fallback_local_model,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
    except Exception:
        fallback_engine = None
    if auto_hint_url:
        # attempt to create the remote engine
        remote_engine = _try_create_remote_engine(
            auto_hint_url,
            auto_hint_api_key,
            remote_model_id,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
        if remote_engine is not None and fallback_engine is not None:
            return FallbackHintEngine(
                remote_engine,
                fallback_engine,
                auto_hint_url,
                console=console,
            )
        if remote_engine is not None:
            return remote_engine
        if fallback_engine is not None:
            console.print()
            console.print(
                "[yellow]Warning: Could not create remote hint engine for"
                f" {auto_hint_url}. Using local model."
                "[/]"
            )
            console.print()
        return fallback_engine
    # no remote URL: use primary local engine, with fallback if needed
    if primary_engine is not None and fallback_engine is not None:
        return FallbackHintEngine(
            primary_engine,
            fallback_engine,
            None,
            console=console,
        )
    if primary_engine is not None:
        return primary_engine
    return fallback_engine


def _try_create_remote_engine(
    url: str,
    api_key: Optional[str],
    model_id: str,
    system_prompt: str | None = None,
    validation_rules: dict[str, list[str]] | None = None,
) -> Any:
    """Attempt to create and verify a RemoteHintEngine.

    Returns the engine wrapped in an adapter that unifies the
    RemoteHintEngine interface (is_loaded, ensure_loaded, model_id,
    generate_hint) with the existing AutoHintEngine interface.

    Returns None if the engine cannot be created (missing deps,
    connection error, etc.).

    """
    try:
        remote = RemoteHintEngine(
            base_url=url,
            api_key=api_key or REMOTE_API_KEY_DEFAULT,
            model_id=model_id,
            system_prompt=system_prompt,
            validation_rules=validation_rules,
        )
        return RemoteEngineAdapter(remote, model_id)
    except Exception:
        return None


@app.callback(invoke_without_command=True)
def gatorgrade(  # noqa: PLR0913, PLR0915
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
            "Directory for configuration files including the"
            " gatorgrade.yml file and other configuration files."
        ),
        show_default=DEFAULT_CONFIG_DIR,
    ),
    report: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--report",
        "-r",
        help=(
            f"A tuple containing the following required values:{NEWLINE}{NEWLINE}"
            f" 1. The destination of the report (either FILE or ENV){NEWLINE}{NEWLINE}"
            f" 2. The format of the report (either JSON or MD){NEWLINE}{NEWLINE}"
            f" 3. The name of the file or environment variable{NEWLINE}{NEWLINE}"
            f" (Use [green]ENV MD GITHUB_STEP_SUMMARY[/green] to make summary in GitHub Actions or"
            f" [green]FILE JSON report.json[/green] to save summary in report.json)."
        ),
        callback=_validate_report,
    ),
    github_env: Tuple[str, str] = typer.Option(
        (None, None),
        "--github-env",
        "-g",
        help=(
            f"A tuple containing the following required values:{NEWLINE}{NEWLINE}"
            f" 1. The format of the data (either JSON or MD){NEWLINE}{NEWLINE}"
            f" 2. The name of the environment variable to set{NEWLINE}{NEWLINE}"
            f" (Use [green]json JSON_REPORT[/green] to store JSON data or"
            f" [green]md MD_REPORT[/green] to store Markdown data in the"
            f" GITHUB_ENV file for downstream steps)."
        ),
        callback=_validate_github_env,
    ),
    output_limit: int = typer.Option(
        5,
        "--output-limit",
        "-o",
        help="Maximum number of diagnostic lines to display for a check (>= 1).",
        callback=_validate_output_limit,
    ),
    baseline_weight: int = typer.Option(
        1,
        "--baseline-weight",
        "-b",
        help="Default weight applied to checks without an explicit weight (>= 1).",
        callback=_validate_baseline_weight,
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
    auto_hint_model: str = typer.Option(
        AUTO_HINT_MODEL_DEFAULT,
        "--auto-hint-model",
        help=(
            "Model identifier for auto-hint generation "
            "(requires --auto-hint). For remote APIs, the default is"
            f" {REMOTE_MODEL_DEFAULT}; for local models, it is"
            f" {DEFAULT_MODEL_ID}."
        ),
        show_default=DEFAULT_MODEL_ID,
    ),
    auto_hint_url: Optional[str] = typer.Option(
        None,
        "--auto-hint-url",
        help=(
            "URL of an OpenAI-compatible API server for remote hint "
            "generation (requires --auto-hint). When provided, the "
            "remote model is used instead of a local model. Falls "
            "back to default local model on any remote URL errors. "
            "Note: requests use the user-agent gatorgrade/0.11.0 "
            "instead of the openai library default, because some "
            "reverse proxies and WAFs (e.g. cloudflare) block the "
            "default openai/python user-agent."
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
        help="Show the GatorGrade version and exit.",
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
        )
        # parse the provided configuration file
        checks, parse_error = parse_config(resolved_filename, baseline_weight)
        # extract the optional project name from the config file
        project_name = get_project_name(resolved_filename)
        # a YAML parsing error occurred and thus the
        # tool should display the error and exit
        if parse_error is not None:
            checks_status = False
            console.print()
            console.print(
                Rule(Text(CONFIG_ERROR_PLURAL_LABEL), style="bright_red")
            )
            console.print(NEWLINE + parse_error)
            console.print()
            console.print(Text(EXIT_MESSAGE))
            console.print()
            console.print(Rule(style="bright_red"))
        # there are valid checks and thus the
        # tool should run them with run_checks
        elif len(checks) > 0:
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
            }
            version_info = {
                GATORGRADE_VERSION_KEY: GATORGRADE_VERSION,
                GATORGRADER_VERSION_KEY: importlib.metadata.version(
                    GATORGRADER_DEPENDENCY
                ),
                PYTHON_INFO_KEY: _get_python_info(),
                PLATFORM_INFO_KEY: _get_platform_info(),
                OS_RELEASE_KEY: _get_os_release(),
            }
            # at the outset, there is no auto-hinting engine
            # unless the person using gatorgrade has explicitly
            # opted in to using auto-hinting both through the
            # command line and through running the tool with
            # the optional dependencies installed (auto-hinting
            # relies on local transformers, which we do not
            # want to load unless the opt-in was made)
            auto_hint_engine = None
            # validate that --auto-hint-model is only used with --auto-hint;
            # the sentinel default catches the case when the user did not
            # explicitly pass the flag
            if not auto_hint and auto_hint_model != AUTO_HINT_MODEL_DEFAULT:
                checks_status = False
                console.print()
                console.print(
                    Rule(
                        CONFIG_ERROR_LABEL,
                        style="bright_red",
                    )
                )
                console.print()
                console.print(
                    f"The {AUTO_HINT_MODEL_FLAG} requires {AUTO_HINT_FLAG} "
                    f"to be enabled for auto-hint generation."
                )
                # console.print()
                console.print(Text(EXIT_MESSAGE))
                console.print()
                console.print(Rule(style="bright_red"))
                sys.exit(FAILURE)
            # auto-hint engine: try to create it if --auto-hint is passed;
            # the engine sources hints from a remote OpenAI-compatible API
            # (when --auto-hint-url is provided) or from a local
            # huggingface transformers model (when no URL is provided).
            # remote engine fails to initialise or returns None for a hint,
            # the program falls back to the local engine.
            # resolve the system prompt and validation rules if specified
            # in the config front matter
            system_prompt = _resolve_system_prompt(
                resolved_filename, resolved_config_dir
            )
            validation_rules = _resolve_validation_rules(
                resolved_filename, resolved_config_dir
            )
            if auto_hint:
                auto_hint_engine = _create_auto_hint_engine(
                    resolved_filename,
                    auto_hint_model,
                    auto_hint_url,
                    auto_hint_api_key,
                    system_prompt=system_prompt,
                    validation_rules=validation_rules,
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
                f"The file {resolved_filename} either does not exist or is not valid."
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


if __name__ == "__main__":
    app()
