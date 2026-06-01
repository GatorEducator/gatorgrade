"""Use Typer to run gatorgrade to run the checks and generate the yml file."""

import platform
import sys
from pathlib import Path
from typing import Tuple

import typer
from rich.console import Console
from rich.emoji import Emoji

from gatorgrade.input.parse_config import parse_config
from gatorgrade.output.output import run_checks

# define the version of gatorgrade; this is used in the --version option
GATORGRADE_VERSION = "0.8.3"

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


def _get_platform_info() -> str:
    """Get the platform information string for Linux."""
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
    return f"Python {version} ({build_no}, {build_date}, {compiler})"


def _get_os_release() -> str:
    """Get the operating system release string for macOS or Windows."""
    if platform.system() == SYSTEM_DARWIN.title():
        release, _, _ = platform.mac_ver()
        if release:
            return f"macOS {release}"
    elif platform.system() == "Windows":
        release, _, _, _ = platform.win32_ver()
        if release:
            return f"Windows {release}"
    return ""


def _version_callback(value: bool) -> None:
    """Print the GatorGrade version and exit when --version is provided."""
    if value:
        lines = [
            f"gatorgrade {GATORGRADE_VERSION} ({_get_platform_info()})",
            _get_python_info(),
        ]
        os_release = _get_os_release()
        if os_release:
            lines.append(os_release)
        console.print("\n".join(lines))
        raise typer.Exit()


@app.callback(invoke_without_command=True)
def gatorgrade(
    ctx: typer.Context,
    filename: Path = typer.Option(
        FILE, "--config", "-c", help="Name of the yml file."
    ),
    report: Tuple[str, str, str] = typer.Option(
        (None, None, None),
        "--report",
        "-r",
        help="A tuple containing the following REQUIRED values: \
            1. The destination of the report (either file or env) \
            2. The format of the report (either json or md) \
            3. the name of the file or environment variable\
            4. use 'env md GITHUB_STEP_SUMMARY' to create GitHub job summary in GitHub Action",
    ),
    run_status_bar: bool = typer.Option(
        False,
        "--status-bar",
        help="Enable a progress bar for checks running/not running.",
    ),
    no_status_bar: bool = typer.Option(
        False, "--no-status-bar", help="Disable the progress bar entirely."
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
    if ctx.invoked_subcommand is None:
        # parse the provided configuration file
        checks = parse_config(filename)
        # there are valid checks and thus the
        # tool should run them with run_checks
        if len(checks) > 0:
            checks_status = run_checks(
                checks, report, run_status_bar, no_status_bar
            )
        # no checks were created and this means
        # that, most likely, the file was not
        # valid and thus the tool cannot run checks
        else:
            checks_status = False
            console.print()
            console.print(
                f"The file {filename} either does not exist or is not valid."
            )
            console.print("Exiting now!")
            console.print()
        # at least one of the checks did not pass or
        # the provided file was not valid and thus
        # the tool should return a non-zero exit
        # code to designate some type of failure
        if checks_status is not True:
            sys.exit(FAILURE)


if __name__ == "__main__":
    app()
