"""Validation functions and constants for GatorGrade CLI arguments.

These validators are called by the Typer option callbacks in main.py
to validate CLI arguments before they reach the main command handler.

The validators raise click.BadParameter when the input is invalid,
which Typer converts into a user-friendly error message.

Usage:
    from gatorgrade.validate import (
        VALID_ENV_VAR_NAME,
        validate_auto_hint_options,
        validate_baseline_weight,
        validate_filter_options,
        validate_github_env,
        validate_output_limit,
        validate_report,
    )
"""

import re
from pathlib import Path
from typing import Optional, Tuple

from click import BadParameter

from gatorgrade.input.filter import (
    DEFAULT_FILTER_BY,
    DEFAULT_FILTER_MODE,
    DEFAULT_FILTER_TYPE,
    FilterBy,
    FilterMode,
    FilterType,
)

# validation constants for the --report option
REPORT_DEST_FILE = "FILE"
REPORT_DEST_ENV = "ENV"
REPORT_TYPE_JSON = "JSON"
REPORT_TYPE_MD = "MD"
VALID_REPORT_DESTS = (REPORT_DEST_FILE, REPORT_DEST_ENV)
VALID_REPORT_TYPES = (REPORT_TYPE_JSON, REPORT_TYPE_MD)

# error message format strings for report validation
REPORT_DEST_ERR_FMT = "First report argument must be '{}' or '{}', got '{}'"
REPORT_TYPE_ERR_FMT = "Second report argument must be '{}' or '{}', got '{}'"
REPORT_PATH_ERR_FMT = (
    "Cannot write report to '{}': directory '{}' does not exist"
)

# error message format strings for github-env validation
GITHUB_ENV_TYPE_ERR_FMT = (
    "First github-env argument must be '{}' or '{}', got '{}'"
)
GITHUB_ENV_NAME_ERR_FMT = (
    "Second github-env argument must be a valid environment variable "
    "name, got '{}'"
)

# error message for the report env var name validation
REPORT_ENV_NAME_ERR_FMT = (
    "Third report argument must be a valid environment variable name "
    "when destination is ENV, got '{}'"
)

# compiled regex for valid environment variable names (must start with
# a letter or underscore, followed by zero or more alphanumeric chars
# or underscores)
VALID_ENV_VAR_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def validate_output_limit(value: int | None) -> int | None:
    """Validate output limit is at least 1 if provided.

    Args:
        value: The output limit value to validate, or None.

    Returns:
        The validated value unchanged.

    Raises:
        BadParameter: If value is a non-positive integer.

    """
    if value is not None and value < 1:
        raise BadParameter("Output limit must be at least 1.")
    return value


def validate_baseline_weight(value: int) -> int:
    """Validate baseline weight is greater than 0.

    Args:
        value: The baseline weight value to validate.

    Returns:
        The validated value unchanged.

    Raises:
        BadParameter: If value is less than 1.

    """
    if value < 1:
        raise BadParameter("Baseline weight must be at least 1.")
    return value


def validate_report(
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

    Args:
        value: A tuple of (destination, format, name).

    Returns:
        The validated tuple unchanged.

    Raises:
        BadParameter: If any validation check fails.

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
        # if there are one or more errors, then raise a BadParameter
        # exception with all of the error messages joined by newlines
        # (reporting all of the possible exceptions instead of failing
        # fast with only the first one should enable a person to better
        # debug command-line arguments)
        if errors:
            raise BadParameter(";\n".join(errors))
    return value


# filter validation constants
FILTER_QUERY_REQUIRED_FMT = (
    "The {} flag requires --filter-query to be specified."
)
FILTER_QUERY_EMPTY_MSG = "Filter query must not be empty."

# flag display names for filter error messages
FILTER_MODE_DISPLAY = "--filter-mode"
FILTER_BY_DISPLAY = "--filter-by"
FILTER_TYPE_DISPLAY = "--filter-type"


def validate_filter_options(
    filter_query: str | None,
    filter_mode: FilterMode,
    filter_by: FilterBy,
    filter_type: FilterType,
) -> list[str]:
    """Validate filter CLI option combinations.

    Checks the following rules:
    - If any of --filter-mode, --filter-by, or --filter-type is
      provided without a non-empty --filter-query, it is an error.
    - If --filter-query is an explicit empty string, it is an error.

    Args:
        filter_query: The --filter-query value, or None.
        filter_mode: The --filter-mode value.
        filter_by: The --filter-by value.
        filter_type: The --filter-type value.

    Returns:
        A list of error message strings. Empty if all checks pass.

    """
    errors: list[str] = []
    # --filter-query explicitly empty is an error
    if filter_query is not None and filter_query == "":
        errors.append(FILTER_QUERY_EMPTY_MSG)
    # mode/by/type without query is an error (only if non-default)
    if not filter_query:
        if filter_mode != DEFAULT_FILTER_MODE:
            errors.append(
                FILTER_QUERY_REQUIRED_FMT.format(FILTER_MODE_DISPLAY)
            )
        if filter_by != DEFAULT_FILTER_BY:
            errors.append(FILTER_QUERY_REQUIRED_FMT.format(FILTER_BY_DISPLAY))
        if filter_type != DEFAULT_FILTER_TYPE:
            errors.append(
                FILTER_QUERY_REQUIRED_FMT.format(FILTER_TYPE_DISPLAY)
            )
    return errors


# error message format strings for auto-hint validation
AUTO_HINT_URL_REQUIRES_AUTO_HINT_FMT = (
    "The {} flag requires {} to be enabled for auto-hint generation."
)
AUTO_HINT_API_KEY_REQUIRES_URL_FMT = (
    "The {} flag requires {} to specify a remote auto-hint server."
)

# flag display names used in error messages
AUTO_HINT_MODEL_DISPLAY = "--auto-hint-model"
AUTO_HINT_URL_DISPLAY = "--auto-hint-url"
AUTO_HINT_API_KEY_DISPLAY = "--auto-hint-api-key"
AUTO_HINT_DISPLAY = "--auto-hint"

# sentinel that indicates the default model was not overridden;
# must match the value in the engine module and main module
AUTO_HINT_MODEL_SENTINEL = "__default_model__"


def validate_auto_hint_options(
    auto_hint: bool,
    auto_hint_model: str,
    auto_hint_url: str | None,
    auto_hint_api_key: str | None,
) -> list[str]:
    """Validate auto-hint CLI option combinations.

    Checks the following rules:
    - --auto-hint-model requires --auto-hint
    - --auto-hint-url requires --auto-hint
    - --auto-hint-api-key requires both --auto-hint and --auto-hint-url

    Args:
        auto_hint: Whether --auto-hint was passed.
        auto_hint_model: The model identifier (or sentinel default).
        auto_hint_url: The remote URL, or None.
        auto_hint_api_key: The API key, or None.

    Returns:
        A list of error message strings. Empty if all checks pass.

    """
    errors: list[str] = []
    # --auto-hint-model requires --auto-hint
    if not auto_hint and auto_hint_model != AUTO_HINT_MODEL_SENTINEL:
        errors.append(
            AUTO_HINT_URL_REQUIRES_AUTO_HINT_FMT.format(
                AUTO_HINT_MODEL_DISPLAY, AUTO_HINT_DISPLAY
            )
        )
    # --auto-hint-url requires --auto-hint
    if not auto_hint and auto_hint_url is not None:
        errors.append(
            AUTO_HINT_URL_REQUIRES_AUTO_HINT_FMT.format(
                AUTO_HINT_URL_DISPLAY, AUTO_HINT_DISPLAY
            )
        )
    # --auto-hint-api-key requires both --auto-hint and --auto-hint-url
    if auto_hint_api_key is not None:
        if not auto_hint:
            errors.append(
                AUTO_HINT_URL_REQUIRES_AUTO_HINT_FMT.format(
                    AUTO_HINT_API_KEY_DISPLAY, AUTO_HINT_DISPLAY
                )
            )
        elif auto_hint_url is None:
            errors.append(
                AUTO_HINT_API_KEY_REQUIRES_URL_FMT.format(
                    AUTO_HINT_API_KEY_DISPLAY, AUTO_HINT_URL_DISPLAY
                )
            )
    return errors


def validate_github_env(
    value: Tuple[Optional[str], Optional[str]],
) -> Tuple[Optional[str], Optional[str]]:
    """Validate github-env tuple arguments up front.

    Validates that the first argument is JSON or MD
    (case-insensitive for backwards compatibility).

    Args:
        value: A tuple of (format, environment_variable_name).

    Returns:
        The validated tuple unchanged.

    Raises:
        BadParameter: If any validation check fails.

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
