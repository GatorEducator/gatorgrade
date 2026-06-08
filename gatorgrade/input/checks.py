"""Define check classes."""

from typing import Any, List


def validate_positive_nonzero_int(value: int, name: str) -> str | None:
    """Return an error message if value is not a positive integer, else None.

    Args:
        value: The value to validate.
        name: The name of the field (used in the error message).

    Returns:
        An error string if invalid, None if valid.

    """
    if not isinstance(value, int) or value <= 0:
        return (
            f"Check {name} must be a positive, non-zero integer, got {value}"
        )
    return None


class ShellCheck:  # pylint: disable=too-few-public-methods
    """Represent a shell check."""

    def __init__(
        self,
        command: str,
        description: str | None = None,
        json_info: dict[str, Any] | str | None = None,
        weight: int = 1,
        outputlimit: int | None = None,
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

        """
        error = validate_positive_nonzero_int(weight, "weight")
        if error:
            raise ValueError(error)
        if outputlimit is not None:
            error = validate_positive_nonzero_int(outputlimit, "outputlimit")
            if error:
                raise ValueError(error)
        self.command = command
        self.description = description if description is not None else command
        self.json_info = json_info
        self.weight = weight
        self.outputlimit = outputlimit


class GatorGraderCheck:  # pylint: disable=too-few-public-methods
    """Represent a GatorGrader check."""

    def __init__(
        self,
        gg_args: List[str],
        json_info: dict[str, Any] | str,
        weight: int = 1,
        outputlimit: int | None = None,
    ):
        """Construct a GatorGraderCheck.

        Args:
            gg_args: The list of arguments to pass to GatorGrader.
            json_info: The all-encompassing check information to include in json output.
            weight: The weight of the check. Must be a positive integer.
            outputlimit: The maximum number of diagnostic lines to display.

        """
        error = validate_positive_nonzero_int(weight, "weight")
        if error:
            raise ValueError(error)
        if outputlimit is not None:
            error = validate_positive_nonzero_int(outputlimit, "outputlimit")
            if error:
                raise ValueError(error)
        self.gg_args = gg_args
        self.json_info = json_info
        self.weight = weight
        self.outputlimit = outputlimit
