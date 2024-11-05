"""Define check result class."""

from typing import Union
import rich


class CheckResult:  # pylint: disable=too-few-public-methods
    """Represent the result of running a check."""

    def __init__(
        self,
        passed: bool,
        description: str,
        json_info,
        path: Union[str, None] = None,
        diagnostic: str = "No diagnostic message available",
    ):
        """Construct a CheckResult.

        Args:
            passed: The passed or failed status of the check result. If true, indicates that the
                check has passed.
            description: The description to use in output.
            json_info: the overall information to be included in json output
            diagnostic: The message to use in output if the check has failed.
        """
        self.passed = passed
        self.description = description
        self.json_info = json_info
        self.diagnostic = diagnostic
        self.path = path
        self.run_command = ""

    def display_result(self, show_diagnostic: bool = False) -> str:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if the check has failed.
                Defaults to false.
        """
        icon = "✓" if self.passed else "✕"
        icon_color = "green" if self.passed else "red"
        message = f"[{icon_color}]{icon}[/]  {self.description}"
        if not self.passed and show_diagnostic:
            message += f"\n[yellow]   → {self.diagnostic}"
        return message

    def __repr__(self):
        return f"CheckResult(passed={self.passed}, description='{self.description}', json_info={self.json_info}, path='{self.path}', diagnostic='{self.diagnostic}', run_command='{self.run_command}')"

    def __str__(self, show_diagnostic: bool = False) -> str:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if the check has failed.
                Defaults to false.
        """
        message = self.display_result(show_diagnostic)
        return message

    def print(self, show_diagnostic: bool = False) -> None:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if the check has failed.
                Defaults to false.
        """
        message = self.display_result(show_diagnostic)
        rich.print(message)
