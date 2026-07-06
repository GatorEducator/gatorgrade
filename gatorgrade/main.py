"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import importlib.metadata
import platform
import re
import sys
from pathlib import Path
from typing import Any, Optional, Tuple

import typer
from click import BadParameter
from rich.console import Console
from rich.emoji import Emoji
from rich.rule import Rule
from rich.text import Text

from gatorgrade.hint.local_engine import (
    DEFAULT_MODEL_ID,
    ENV_CACHE_DIR,
    AutoHintEngine,
    _platform_model_cache_dir,
)
from gatorgrade.hint.remote_engine import (
    REMOTE_API_KEY_DEFAULT,
    RemoteHintEngine,
)
from gatorgrade.input.parse_config import (
    ENV_CONFIG_DIR,
    _platform_config_dir,
    get_auto_hint_model,
    get_config_dir,
    get_due_date,
    get_due_date_aliases_present,
    get_project_name,
    has_due_date_field,
    parse_config,
    resolve_config_path,
)
from gatorgrade.output.output import run_checks

# define the version of gatorgrade; this is used in the --version option
# and must always match the value in the pyproject.toml file
GATORGRADE_VERSION = "0.11.0"

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

# define constants for the platform information that is displayed
# by the --version option, mirroring the format used by uv; the
# arch and system combination is already unique across platforms
# (e.g., x86_64 + linux, arm64 + darwin, AMD64 + windows), so the
# vendor field from Rust's target triple is omitted because Python
# cannot determine it and it would always be "unknown"
UNKNOWN_PLATFORM = "unknown"
GATORGRADER_DEPENDENCY = "gatorgrader"

# define constants related to platform details
LIBC_GNU = "gnu"
LIBC_MUSL = "musl"
LIBC_NONE = "none"
LIBC_MSVC = "msvc"
SYSTEM_DARWIN = "darwin"
SYSTEM_LINUX = "linux"
SYSTEM_WINDOWS = "windows"
_LIBC_BY_SYSTEM = {
    SYSTEM_DARWIN: LIBC_NONE,
    SYSTEM_WINDOWS: LIBC_MSVC,
}

# operating system display names for version output
OS_DARWIN = "Darwin"
OS_LINUX = "Linux"
OS_MACOS = "MacOS"
OS_WINDOWS = "Windows"

# program and language display names for version output
GATORGRADE_NAME = "gatorgrade"
GATORGRADER_NAME = "GatorGrader"
PYTHON_NAME = "Python"

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

# report argument constants
REPORT_DEST_FILE = "FILE"
REPORT_DEST_ENV = "ENV"
REPORT_TYPE_JSON = "JSON"
REPORT_TYPE_MD = "MD"
VALID_REPORT_DESTS = (REPORT_DEST_FILE, REPORT_DEST_ENV)
VALID_REPORT_TYPES = (REPORT_TYPE_JSON, REPORT_TYPE_MD)
REPORT_DEST_ERR_FMT = "First report argument must be '{}' or '{}', got '{}'"
REPORT_TYPE_ERR_FMT = "Second report argument must be '{}' or '{}', got '{}'"
REPORT_PATH_ERR_FMT = (
    "Cannot write report to '{}': directory '{}' does not exist"
)
GITHUB_ENV_TYPE_ERR_FMT = (
    "First github-env argument must be '{}' or '{}', got '{}'"
)
GITHUB_ENV_NAME_ERR_FMT = (
    "Second github-env argument must be a valid environment variable name, "
    "got '{}'"
)
REPORT_ENV_NAME_ERR_FMT = (
    "Third report argument must be a valid environment variable name when "
    "destination is ENV, got '{}'"
)
VALID_ENV_VAR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_output_limit(value: int | None) -> int | None:
    """Validate output limit is at least 1 if provided."""
    if value is not None and value < 1:
        raise BadParameter("Output limit must be at least 1.")
    return value


def _validate_baseline_weight(value: int) -> int:
    """Validate baseline weight is greater than 0."""
    if value < 1:
        raise BadParameter("Baseline weight must be at least 1.")
    return value


def _validate_report(
    value: Tuple[Optional[str], Optional[str], Optional[str]],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Validate report tuple arguments up front to avoid crashes later.

    Validates that:
    - First argument is FILE or ENV (case-insensitive for backwards
      compatibility)
    - Second argument is JSON or MD (case-insensitive for backwards
      compatibility)
    - When the destination is not explicitly ENV, validate the third
      argument's parent directory exists (it is a file path)

    """
    if any(v is not None for v in value):
        errors = []
        if value[0] is not None and value[0].upper() not in VALID_REPORT_DESTS:
            errors.append(
                REPORT_DEST_ERR_FMT.format(
                    REPORT_DEST_FILE, REPORT_DEST_ENV, value[0]
                )
            )
        if value[1] is not None and value[1].upper() not in VALID_REPORT_TYPES:
            errors.append(
                REPORT_TYPE_ERR_FMT.format(
                    REPORT_TYPE_JSON, REPORT_TYPE_MD, value[1]
                )
            )
        if value[0] is not None and value[0].upper() != REPORT_DEST_ENV:
            assert value[2] is not None  # validated earlier
            file_path = Path(value[2])
            parent_dir = file_path.resolve().parent
            if not parent_dir.exists():
                errors.append(REPORT_PATH_ERR_FMT.format(value[2], parent_dir))
        elif value[0] is not None and value[2] is not None:
            if not VALID_ENV_VAR_NAME.fullmatch(value[2]):
                errors.append(REPORT_ENV_NAME_ERR_FMT.format(value[2]))
        # if there are one or more errors, then raise a BadParameter exception
        # with all of the error messages joined by newlines (reporting all
        # of the possible exceptions instead of failing fast with only the
        # first one should enable a person to better debug command-line arguments)
        if errors:
            raise BadParameter(";\n".join(errors))
    return value


def _validate_github_env(
    value: Tuple[Optional[str], Optional[str]],
) -> Tuple[Optional[str], Optional[str]]:
    """Validate github-env tuple arguments up front.

    Validates that the first argument is JSON or MD
    (case-insensitive for backwards compatibility).

    """
    if any(v is not None for v in value):
        errors = []
        if value[0] is not None and value[0].upper() not in VALID_REPORT_TYPES:
            errors.append(
                GITHUB_ENV_TYPE_ERR_FMT.format(
                    REPORT_TYPE_JSON, REPORT_TYPE_MD, value[0]
                )
            )
        if value[1] is not None and not VALID_ENV_VAR_NAME.fullmatch(value[1]):
            errors.append(GITHUB_ENV_NAME_ERR_FMT.format(value[1]))
        if errors:
            raise BadParameter(";\n".join(errors))
    return value


def _get_platform_info() -> str:
    """Get the platform information string for any platform."""
    arch = platform.machine() or UNKNOWN_PLATFORM
    system = platform.system().lower() or UNKNOWN_PLATFORM
    libc_name, _ = platform.libc_ver()
    if system == SYSTEM_LINUX:
        libc_lower = libc_name.lower()
        libc = (
            LIBC_MUSL
            if LIBC_MUSL in libc_lower
            else LIBC_GNU
            if libc_name
            else UNKNOWN_PLATFORM
        )
    elif system in _LIBC_BY_SYSTEM:
        libc = _LIBC_BY_SYSTEM[system]
    else:
        libc = UNKNOWN_PLATFORM
    return f"{arch}-{system}-{libc}"


def _get_python_info() -> str:
    """Get the Python version, build, and compiler information string."""
    version = platform.python_version()
    build_no, build_date = platform.python_build()
    compiler = platform.python_compiler().strip()
    return f"{PYTHON_NAME} {version} ({build_no}, {build_date}, {compiler})"


def _get_gatorgrade_info() -> str:
    """Get the parenthetic GatorGrade info string with the GatorGrader version."""
    # use the importlib.metadata version function to get the
    # version of the gatorgrader dependency (note that this works correctly
    # even when gatorgrade is published to PyPI and download and used because
    # of the fact that gatorgrader is a required and packaged dependnecy)
    gatorgrader_version = importlib.metadata.version(GATORGRADER_DEPENDENCY)
    return f"{GATORGRADER_NAME} {gatorgrader_version}"


def _get_os_release() -> str:
    """Get the operating system release string for Linux, macOS, or Windows."""
    parenthetic_platform_string = f"({_get_platform_info()})"
    if platform.system() == OS_LINUX:
        kernel = platform.release()
        if kernel:
            return f"{OS_LINUX} {kernel} {parenthetic_platform_string}"
    elif platform.system() == OS_DARWIN:
        release, _, _ = platform.mac_ver()
        if release:
            return f"{OS_MACOS} {release} {parenthetic_platform_string}"
    elif platform.system() == OS_WINDOWS:
        release, _, _, _ = platform.win32_ver()
        if release:
            return f"{OS_WINDOWS} {release} {parenthetic_platform_string}"
    return ""


def _version_callback(value: bool) -> None:
    """Print the GatorGrade version and exit when --version is provided."""
    if value:
        console.print(
            f"{GATORGRADE_NAME} {GATORGRADE_VERSION} ({_get_gatorgrade_info()})"
        )
        console.print(_get_python_info())
        os_release = _get_os_release()
        if os_release:
            console.print(os_release)
        # show the path-related environment variables and resolved
        # defaults so users know which paths affect gatorgrade
        import os  # noqa: PLC0415

        models_override = os.environ.get(ENV_CACHE_DIR)
        config_override = os.environ.get(ENV_CONFIG_DIR)
        models_default = str(_platform_model_cache_dir())
        config_default = str(_platform_config_dir())

        def _fmt_env(name: str, override: str | None, default: str) -> Text:
            """Format a single environment variable line for display."""
            result = Text()
            result.append(f"{name} is ")
            result.append(
                override if override else "(unset with",
                style="" if override else "dim",
            )
            result.append(
                f" default: {default})",
                style="dim",
            )
            return result

        for env_line in [
            _fmt_env(ENV_CACHE_DIR, models_override, models_default),
            _fmt_env(ENV_CONFIG_DIR, config_override, config_default),
        ]:
            console.print(env_line)
        raise typer.Exit()


def _create_auto_hint_engine(
    filename: Path,
    auto_hint_model: str,
    auto_hint_url: Optional[str],
    auto_hint_api_key: Optional[str],
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

    Returns:
        An AutoHintEngine instance, or None if creation fails.

    """
    # resolve the model ID from the CLI, config file, or default
    model_id = auto_hint_model
    if (
        not model_id
        or not model_id.strip()
        or model_id == AUTO_HINT_MODEL_DEFAULT
    ):
        config_model = get_auto_hint_model(filename)
        model_id = config_model or DEFAULT_MODEL_ID
    if auto_hint_url:
        # attempt the remote engine first
        engine = _try_create_remote_engine(
            auto_hint_url,
            auto_hint_api_key,
            model_id,
        )
        if engine is not None:
            return engine
        # remote failed; warn and fall through to the local engine
        console.print()
        console.print(
            "[yellow]Warning: Could not reach remote hint server at"
            f" {auto_hint_url}. Falling back to local model"
            f" ({model_id}).[/]"
        )
        console.print()
    # fall back to the local engine
    try:
        return AutoHintEngine(model_id=model_id)
    except Exception:
        return None


def _try_create_remote_engine(
    url: str,
    api_key: Optional[str],
    model_id: str,
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
        )
        return RemoteEngineAdapter(remote, model_id)
    except Exception:
        return None


class RemoteEngineAdapter:
    """Adapter for wrapping RemoteHintEngine with the AutoHintEngine interface.

    The display logic in output.py calls:
    - engine.is_loaded
    - engine.ensure_loaded()
    - engine.model_id
    - engine.generate_hint(...)

    All of these are forwarded to the wrapped remote engine.

    """

    def __init__(self, remote_engine: RemoteHintEngine, model_id: str):
        """Initialise the adapter.

        Args:
            remote_engine: The RemoteHintEngine instance to wrap.
            model_id: The model identifier string for display.

        """
        self._remote = remote_engine
        self._model_id = model_id

    @property
    def is_loaded(self) -> bool:
        """The remote engine is always considered loaded."""
        return True

    def ensure_loaded(self) -> None:
        """No-op for the remote engine."""

    @property
    def model_id(self) -> str:
        """Return the model identifier for display."""
        return f"{self._model_id}"

    def generate_hint(
        self,
        description: str,
        diagnostic: str = "",
        command: str = "",
        file_content: str = "",
    ) -> tuple[Optional[str], bool]:
        """Delegate hint generation to the remote engine."""
        return self._remote.generate_hint(
            description=description,
            diagnostic=diagnostic,
            command=command,
            file_content=file_content,
        )


@app.callback(invoke_without_command=True)
def gatorgrade(  # noqa: PLR0913, PLR0915
    ctx: typer.Context,
    filename: Path = typer.Option(
        FILE, "--config", "-c", help="Name of the yml file."
    ),
    config_dir: Optional[Path] = typer.Option(
        None,
        "--config-dir",
        "-C",
        help=(
            "Directory for configuration files including the"
            " gatorgrade.yml file, models, and other settings."
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
            "Hugging Face or OpenAI-API-compatible model identifier for auto-hint generation "
            "(requires --auto-hint)."
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
            "back to default local model on connection errors."
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
            if auto_hint:
                auto_hint_engine = _create_auto_hint_engine(
                    resolved_filename,
                    auto_hint_model,
                    auto_hint_url,
                    auto_hint_api_key,
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
