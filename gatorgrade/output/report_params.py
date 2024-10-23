"""Define a class of the called ReportParms for the --report tag."""

from enum import Enum


class ReportParamsLocation(str, Enum):
    """Define the location for the parameters of reporting and storing gatorgrade checks."""

    file = "file"
    env = "env"

    def __str__(self):
        """Define a default string representation."""
        return self.value

class ReportParamsType(str, Enum):
    """Define the type of type to store the data in."""

    json = "json"
    md = "md"

    def __str__(self):
        """Define a default string representation."""
        return self.value

class ReportParamsStoringName(str, Enum):
    """Define the type of type to store the data in."""

    file: str
    github = "github"

    def __str__(self):
        """Define a default string representation."""
        return self.value

# example to references for the form
# class ShellCheck:  # pylint: disable=too-few-public-methods
#     """Represent a shell check."""

#     def __init__(self, command: str, description: str = None, json_info=None):  # type: ignore
#         """Construct a ShellCheck.

#         Args:
#             command: The command to run in a shell.
#             description: The description to use in output.
#                 If no description is given, the command is used as the description.
#             json_info: The all-encompassing check information to include in json output.
#                 If none is given, command is used
#         """
#         self.command = command
#         self.description = description if description is not None else command
#         self.json_info = json_info


# another idea/example
# class Triangle:
#     """Define the Triangle dataclass for constant(s)."""

#     Equilateral: str
#     Isosceles: str
#     Scalene: str
