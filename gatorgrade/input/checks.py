"""Define check classes."""

from typing import Any, List

NEWLINE = "\n"
WEIGHT_FIELD = "weight"
OUTPUTLIMIT_FIELD = "outputlimit"


def validate_positive_nonzero_int(value: int, name: str) -> str | None:
    """Return an error message if value is not a positive integer, else None.

    Args:
        value: The value to validate.
        name: The name of the field (used in the error message).

    Returns:
        An error string if invalid, None if valid.

    """
    # confirm that the value is an integer (and not a boolean, which is also
    # a subclass of int) and that it is greater than 0; if these conditions
    # are not met this this parameter is not a positive non-zero integer
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        return (
            f"Check {name} must be a positive, non-zero integer, got {value}"
        )
    return None


class ShellCheck:  # pylint: disable=too-few-public-methods
    """Represent a shell check."""

    def __init__(  # noqa: PLR0913
        self,
        command: str,
        description: str | None = None,
        json_info: dict[str, Any] | str | None = None,
        weight: int = 1,
        outputlimit: int | None = None,
        hint: str | None = None,
        check_id: str | None = None,
    ):
        """Construct a ShellCheck.

        Args:
            command: The command to run in a shell.
            description: The description to use in output.
                If no description is given, the command is used as the description.
            json_info: The all-encompassing check information to include in json output.
                If none is given, command is used
            weight: The weight of the check. Must be a positive integer.
            outputlimit: The maximum number of diagnostic lines to display.
            hint: An optional hint message shown when the check fails.
            check_id: An optional SHA-256 hash uniquely identifying this check.

        """
        # validate the weight and the outputlimit so that they
        # are confirmed to be positive integers before setting any attributes
        errors = []
        error = validate_positive_nonzero_int(weight, WEIGHT_FIELD)
        if error:
            errors.append(error)
        if outputlimit is not None:
            error = validate_positive_nonzero_int(
                outputlimit, OUTPUTLIMIT_FIELD
            )
            if error:
                errors.append(error)
        # if there are any errors, raise a ValueError with all
        # of the error messages joined by newlines
        if errors:
            raise ValueError(NEWLINE.join(errors))
        # otherwise, set the attributes
        self.command = command
        self.description = description if description is not None else command
        self.json_info = json_info
        self.weight = weight
        self.outputlimit = outputlimit
        self.hint = hint
        self.check_id = check_id


class GatorGraderCheck:  # pylint: disable=too-few-public-methods
    """Represent a GatorGrader check."""

    def __init__(  # noqa: PLR0913
        self,
        gg_args: List[str],
        json_info: dict[str, Any] | str,
        weight: int = 1,
        outputlimit: int | None = None,
        hint: str | None = None,
        check_id: str | None = None,
    ):
        """Construct a GatorGraderCheck.

        Args:
            gg_args: The list of arguments to pass to GatorGrader.
            json_info: The all-encompassing check information to include in json output.
            weight: The weight of the check. Must be a positive integer.
            outputlimit: The maximum number of diagnostic lines to display.
            hint: An optional hint message shown when the check fails.
            check_id: An optional SHA-256 hash uniquely identifying this check.

        """
        errors = []
        # if there are any errors, raise a ValueError with all
        # of the error messages joined by newlines
        error = validate_positive_nonzero_int(weight, WEIGHT_FIELD)
        if error:
            errors.append(error)
        if outputlimit is not None:
            error = validate_positive_nonzero_int(
                outputlimit, OUTPUTLIMIT_FIELD
            )
            if error:
                errors.append(error)
        if errors:
            raise ValueError(NEWLINE.join(errors))
        # otherwise, set the attributes
        self.gg_args = gg_args
        self.json_info = json_info
        self.weight = weight
        self.outputlimit = outputlimit
        self.hint = hint
        self.check_id = check_id
