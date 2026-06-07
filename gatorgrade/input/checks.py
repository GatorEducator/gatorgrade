"""Define check classes."""

from typing import Any, List


class ShellCheck:  # pylint: disable=too-few-public-methods
    """Represent a shell check."""

    def __init__(
        self,
        command: str,
        description: str | None = None,
        json_info: dict[str, Any] | str | None = None,
        weight: int | float = 1,
    ):
        """Construct a ShellCheck.

        Args:
            command: The command to run in a shell.
            description: The description to use in output.
                If no description is given, the command is used as the description.
            json_info: The all-encompassing check information to include in json output.
                If none is given, command is used
            weight: The weight of the check. Must be greater than 0.

        """
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError(
                f"Check weight must be a number greater than 0, got {weight}"
            )
        self.command = command
        self.description = description if description is not None else command
        self.json_info = json_info
        self.weight = weight


class GatorGraderCheck:  # pylint: disable=too-few-public-methods
    """Represent a GatorGrader check."""

    def __init__(
        self,
        gg_args: List[str],
        json_info: dict[str, Any] | str,
        weight: int | float = 1,
    ):
        """Construct a GatorGraderCheck.

        Args:
            gg_args: The list of arguments to pass to GatorGrader.
            json_info: The all-encompassing check information to include in json output.
            weight: The weight of the check. Must be greater than 0.

        """
        if not isinstance(weight, (int, float)) or weight <= 0:
            raise ValueError(
                f"Check weight must be a number greater than 0, got {weight}"
            )
        self.gg_args = gg_args
        self.json_info = json_info
        self.weight = weight
