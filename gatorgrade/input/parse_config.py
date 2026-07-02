"""Returns the list of commands to be run through gatorgrader."""

import datetime
from pathlib import Path
from typing import Any, List, Tuple

import yaml

from gatorgrade.input.checks import validate_positive_nonzero_int
from gatorgrade.input.command_line_generator import generate_checks
from gatorgrade.input.in_file_path import (
    DATA_WITH_SETUP_LENGTH,
    parse_yaml_file,
    reformat_yaml_data,
)

# importantly, note that the ordering of the front-matter field
# names inside of the DUE_DATE_ALIASES tuple is important because
# the first alias to match is the one that will be extracted;
# using the due_date alias first means that it will be the
# one given priority if more than one is found in the front-matter
# of a gatorgrade configuration file

NAME_FIELD = "name"
DUE_DATE_FIELD = "due_date"
DUE_DATE_ALIASES = ("due_date", "duedate", "due", "date")
BASELINE_WEIGHT_FIELD = "baseline_weight"


def get_project_name(file: Path) -> str | None:
    """Extract the optional project name from a gatorgrade YAML config file.

    The project name is specified in the front matter of the YAML file as:

        name: "Theory of Computation Final Examination"
        setup: |
          ...
        ---
        - checks...

    Args:
        file: Path to the gatorgrade YAML configuration file.

    Returns:
        The project name string if specified, or None if not present.

    """
    try:
        parsed_yaml_file = parse_yaml_file(file)
        if len(parsed_yaml_file) >= DATA_WITH_SETUP_LENGTH and isinstance(
            parsed_yaml_file[0], dict
        ):
            return parsed_yaml_file[0].get(NAME_FIELD, None)
    except (yaml.YAMLError, OSError):
        pass
    return None


def _parse_due_date_value(
    value: Any,
) -> tuple[datetime.datetime | None, str | None]:
    """Parse a due date value from the YAML front matter.

    Supports quoted strings in ISO 8601 format, unquoted YAML datetime
    objects, and unquoted YAML date objects. Timezone-aware datetimes
    are converted to naive local time on computer running gatorgrade.

    Args:
        value: The raw value from the YAML front matter.

    Returns:
        A tuple of (datetime, None) on success, or (None, error_message)
        if the value could not be parsed.

    """
    try:
        if isinstance(value, str):
            dt = datetime.datetime.fromisoformat(value)
        elif isinstance(value, datetime.datetime):
            dt = value
        elif isinstance(value, datetime.date):
            dt = datetime.datetime.combine(value, datetime.time.min)
        else:
            return None, (f"Unsupported due date type: {type(value).__name__}")
    except ValueError as e:
        return None, f"Could not parse due date: {e}"
    # convert timezone-aware datetimes to naive local time; note that
    # if this conversion is not done and the creator of the gatorgrade
    # configuration file has used a datetime with a timezeone, then
    # the program will crash if two different types of datetime
    # objects (they are different types) are compared to each other
    if dt.tzinfo is not None:
        dt = dt.astimezone().replace(tzinfo=None)
    return dt, None


def _get_due_date_value(
    front_matter: dict,
) -> tuple[Any | None, str | None]:
    """Find the due date value from the front matter, trying all aliases.

    Args:
        front_matter: The YAML front matter dictionary.

    Returns:
        A tuple of (raw_value, field_name) or (None, None) if no alias
        is found. The first matching alias in DUE_DATE_ALIASES is used.

    """
    # search through each of the due date aliases
    for alias in DUE_DATE_ALIASES:
        # if one of the due date aliases is found,
        # then extract it and the due date
        if alias in front_matter:
            return front_matter[alias], alias
    # there were no due dates found inside of the
    # front matter and thus no checking for due
    # dates will occur and no diagnostics will appear
    # at the end of the output to highlight project status
    # from the perspective of the due date
    return None, None


def get_due_date_aliases_present(file: Path) -> list[str]:
    """Return all due date alias field names found in the front matter.

    Args:
        file: Path to the gatorgrade YAML configuration file.

    Returns:
        A list of field names found (e.g. ["due_date", "due"]), or an
        empty list if none are present in the front matter of the YAML file.

    """
    result: list[str] = []
    try:
        # parse the YAML file using parse_yaml_file provided by gatorgrade
        parsed_yaml_file = parse_yaml_file(file)
        # if there were no due dates, then return the
        # empty result list, meaning that no due date
        # display and details will appear in the output
        if not (
            len(parsed_yaml_file) >= DATA_WITH_SETUP_LENGTH
            and isinstance(parsed_yaml_file[0], dict)
        ):
            return result
        # check for each of the due date aliases and add them to the result list
        for alias in DUE_DATE_ALIASES:
            if alias in parsed_yaml_file[0]:
                result.append(alias)
        return result
    # if there was a parsing exception, then return the
    # current state of the list, which should be empty
    except (yaml.YAMLError, OSError):
        return result


def get_due_date(
    file: Path,
) -> tuple[datetime.datetime | None, str | None]:
    """Extract the optional due date from a gatorgrade YAML config file.

    The due date can be specified with any of these field names:
    due_date (recommended), duedate, due, or date.

        due_date: "2026-12-15T23:59:00"
        setup: |
          ...
        ---
        - checks...

    Both ISO 8601 datetime strings ("2026-12-15T23:59:00") and date-only
    strings ("2026-12-15") are accepted. Date-only strings are treated as
    midnight on that date. Timezone-aware datetime strings are converted
    to naive local time. If there is more than one of the approved fields
    in the front matter about the due date, then the one called "due_date"
    is used and a warning message is displayed. This warning message is
    largely for the benefit of instructors who do not create the due date
    in the front matter using the approved approach for due dates.

    Args:
        file: Path to the gatorgrade YAML configuration file.

    Returns:
        A tuple of (datetime, None) on success, (None, error_message) on
        parse failure, or (None, None) if no due date is present.

    """
    # try to parse the YAML file and extract the due date from
    # the YAML front matter; this assumes that the date must be
    # in the standard ISO 8601 format for specifying dates
    try:
        parsed_yaml_file = parse_yaml_file(file)
        if not (
            len(parsed_yaml_file) >= DATA_WITH_SETUP_LENGTH
            and isinstance(parsed_yaml_file[0], dict)
        ):
            return None, None
        value, alias = _get_due_date_value(parsed_yaml_file[0])
        if value is None:
            return None, None
        due_date, parse_error = _parse_due_date_value(value)
        if parse_error:
            return None, f"Invalid value for '{alias}': {parse_error}"
        return due_date, None
    except yaml.YAMLError as e:
        return None, f"Could not parse YAML front matter: {e}"
    except OSError as e:
        return None, f"Could not read configuration file: {e}"


def has_due_date_field(file: Path) -> bool:
    """Check whether the YAML front matter contains a due date field.

    The accepted field names are: due_date, duedate, due, and date.

    Args:
        file: Path to the gatorgrade YAML configuration file.

    Returns:
        True if any due date alias is present, False otherwise.

    """
    # determine whether or not there is any type of due
    # date inside of the front matter of the YAML file
    try:
        parsed_yaml_file = parse_yaml_file(file)
        if not (
            len(parsed_yaml_file) >= DATA_WITH_SETUP_LENGTH
            and isinstance(parsed_yaml_file[0], dict)
        ):
            return False
        return any(alias in parsed_yaml_file[0] for alias in DUE_DATE_ALIASES)
    except (yaml.YAMLError, OSError):
        return False


def parse_config(
    file: Path, baseline_weight: int = 1
) -> Tuple[List[Any], str | None]:
    """Parse the input YAML file and generate specified checks.

    Args:
        file: YAML file containing gatorgrade and shell command checks
        baseline_weight: Default weight for checks that do not specify one
    Returns:
        Returns a tuple of (checks, error_message). When successful,
        checks contains the list of checks and error_message is None.
        On failure, checks is empty and error_message contains details.

    """
    # validate the baseline_weight so that it is a positive integer;
    # note that this is already checked by the validation of the
    # command-line arguments provided by the person using the program;
    # however, adding the check here in case this function is called
    # directly without going through the command-line argument validation
    error = validate_positive_nonzero_int(
        baseline_weight, BASELINE_WEIGHT_FIELD
    )
    if error:
        return [], error
    try:
        # parse the YAML file using parse_yaml_file provided by gatorgrade
        parsed_yaml_file = parse_yaml_file(file)
        # the parsed YAML file contains some contents in a list and thus
        # the tool should generate a GatorGrader check for each element in list
        if len(parsed_yaml_file) > 0:
            # after reformatting the parse YAML file,
            # use it to generate all of the checks;
            # these will be valid checks that are now
            # ready for execution with this tool
            parse_con = generate_checks(
                reformat_yaml_data(parsed_yaml_file), baseline_weight
            )
            return parse_con, None
        # return an empty list because of the fact that the
        # parsing process did not return a list with content;
        # allow the calling function to handle the empty list
        return [], None
    except (yaml.YAMLError, ValueError, TypeError, IndexError) as error:
        return [], str(error)
