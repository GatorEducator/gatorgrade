"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import importlib.metadata
import platform
import sys
from pathlib import Path
from typing import Tuple

import typer
from click import BadParameter
from rich.console import Console
from rich.emoji import Emoji
from rich.rule import Rule

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

# define the version of gatorgrade; this is used in the --version option
GATORGRADE_VERSION = "0.9.0"

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
    help=f"{gatorgrade_emoji} Run the GatorGrader checks in the specified gatorgrade.yml file.",
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
EXIT_MESSAGE = "Exiting now!"


def _validate_output_limit(value: int | None) -> int | None:
    """Validate output limit is at least 1 if provided."""
    if value is not None and value < 1:
        raise BadParameter("Output limit must be at least 1.")
    return value


def _validate_baseline_weight(value: int) -> int:
    """Validate baseline weight is greater than 0."""
    if value is not None and value < 1:
        raise BadParameter("Baseline weight must be at least 1.")
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
        lines = [
            f"{GATORGRADE_NAME} {GATORGRADE_VERSION} ({_get_gatorgrade_info()})",
            _get_python_info(),
        ]
        os_release = _get_os_release()
        if os_release:
            lines.append(os_release)
        console.print(NEWLINE.join(lines))
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def gatorgrade(  # noqa: PLR0913
    ctx: typer.Context,
    filename: Path = typer.Option(
        FILE, "--config", "-c", help="Name of the yml file."
    ),
    report: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--report",
        "-r",
        help=(
            f"A tuple containing the following REQUIRED values:{NEWLINE}{NEWLINE}"
            f" 1. The destination of the report (either file or env){NEWLINE}{NEWLINE}"
            f" 2. The format of the report (either json or md){NEWLINE}{NEWLINE}"
            f" 3. The name of the file or environment variable{NEWLINE}{NEWLINE}"
            f" (Use env md GITHUB_STEP_SUMMARY to create job summary in GitHub Actions)"
        ),
    ),
    output_limit: int = typer.Option(
        1,
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
    run_status_bar: bool = typer.Option(
        False,
        "--progress-bar",
        help="Enable a progress bar for checks.",
    ),
    no_status_bar: bool = typer.Option(
        False, "--no-progress-bar", help="Disable a progress bar for checks."
    ),
    _version: bool = typer.Option(
        False,
        "--version",
        callback=_version_callback,
        is_eager=True,
        help="Show the GatorGrade version and exit.",
    ),
) -> None:
    """Run the GatorGrader checks in the specified gatorgrade.yml file."""
    # if ctx.subcommand is None then this means
    # that, by default, gatorgrade should run in checking mode
    # (note that the current implementation of the tool only
    # supports checking mode as all others are deprecated)
    if ctx.invoked_subcommand is None:
        # parse the provided configuration file
        checks, parse_error = parse_config(filename, baseline_weight)
        # a YAML parsing error occurred and thus the
        # tool should display the error and exit
        if parse_error is not None:
            checks_status = False
            console.print()
            console.print(Rule("Configuration Error", style="bright_red"))
            console.print(NEWLINE + parse_error)
            console.print(NEWLINE + EXIT_MESSAGE + NEWLINE)
            console.print(Rule(style="bright_red"))
        # there are valid checks and thus the
        # tool should run them with run_checks
        elif len(checks) > 0:
            checks_status = run_checks(
                checks,
                report,
                run_status_bar,
                no_status_bar,
                output_limit,
            )
        # no checks were created and this means
        # that, most likely, the file was not
        # valid and thus the tool cannot run checks
        else:
            checks_status = False
            console.print()
            console.print(Rule("Configuration Error", style="bright_red"))
            console.print()
            console.print(
                f"The file {filename} either does not exist or is not valid."
            )
            console.print(NEWLINE + EXIT_MESSAGE + NEWLINE)
            console.print(Rule(style="bright_red"))
        # at least one of the checks did not pass or
        # the provided file was not valid and thus
        # the tool should return a non-zero exit
        # code to designate some type of failure
        if checks_status is not True:
            sys.exit(FAILURE)


if __name__ == "__main__":
    app()
