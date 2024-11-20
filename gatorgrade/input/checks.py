"""Define check classes."""

from typing import List

class ShellCheck:  # pylint: disable=too-few-public-methods
    """Represent a shell check."""

    def __init__(self, command: str, description: str = None, json_info=None, gg_args: List[str] = None):  # type: ignore
        """Construct a ShellCheck.

        Args:
            command: The command to run in a shell.
            description: The description to use in output.
                If no description is given, the command is used as the description.
            json_info: The all-encompassing check information to include in json output.
                If none is given, command is used.
            options: Additional options for the shell check as a dictionary.
        """
        self.command = command
        self.description = description if description is not None else command
        self.json_info = json_info
        self.gg_args = gg_args if gg_args is not None else []

    def __str__(self):
        """Return a string representation of the ShellCheck."""
        return f"ShellCheck(command={self.command}, description={self.description}, json_info={self.json_info}, gg_args={self.gg_args})"



class GatorGraderCheck:  # pylint: disable=too-few-public-methods
    """Represent a GatorGrader check."""

    def __init__(self, gg_args: List[str], json_info):
        """Construct a GatorGraderCheck.

        Args:
            gg_args: The list of arguments to pass to GatorGrader.
            json_info: The all-encompassing check information to include in json output.
        """
        self.gg_args = gg_args
        self.json_info = json_info
