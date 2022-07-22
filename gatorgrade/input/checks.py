"""Define check classes."""
from typing import List


class ShellCheck:  # pylint: disable=too-few-public-methods
    """Represent a shell check."""

    def __init__(self, command: str, description: str = None):
        """Construct a ShellCheck.

        Args:
            command: The command to run in a shell.
            description: The description to use in output.
                If no description is given, the command is used as the description.
        """
        self.command = command
        self.description = description if description is not None else command


class GatorGraderCheck:  # pylint: disable=too-few-public-methods
    """Represent a GatorGrader check."""

    def __init__(self, gg_args: List[str]):
        """Construct a GatorGraderCheck.

        Args:
            gg_args: The list of arguments to pass to GatorGrader.
        """
        self.gg_args = gg_args
