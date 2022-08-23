"""Define check result class."""
import rich
from json import JSONEncoder


class CheckResult:  # pylint: disable=too-few-public-methods
    """Represent the result of running a check."""

    def __init__(
            self,
            passed: bool,
            description: str,
            diagnostic: str = "No diagnostic message available",
    ):
        """Construct a CheckResult.

        Args:
            passed: The passed or failed status of the check result. If true, indicates that the
                check has passed.
            description: The description to use in output.
            diagnostic: The message to use in output if the check has failed.
        """
        self.passed = passed
        self.description = description
        self.diagnostic = diagnostic

    def print(self, show_diagnostic: bool = False) -> None:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is avaiable, then the output will say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if the check has failed.
                Defaults to false.
        """
        icon = "✔" if self.passed else "✘"
        icon_color = "green" if self.passed else "red"

        rich.print(f"[{icon_color}]{icon}[/]  {self.description}")

        if not self.passed and show_diagnostic:
            rich.print(f"[yellow]   → {self.diagnostic}")


class CheckJsonEncoder(JSONEncoder):
    def default(self, o):
        return o.__dict__
