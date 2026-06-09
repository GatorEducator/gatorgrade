"""Define check result class."""

from typing import Any, Dict, Optional, Union

import rich


class CheckResult:  # pylint: disable=too-few-public-methods
    """Represent the result of running a check."""

    def __init__(  # noqa: PLR0913
        self,
        passed: bool,
        description: str,
        json_info: Union[Dict[str, Any], str, None],
        path: Optional[str] = None,
        diagnostic: str = "No diagnostic message available",
        weight: int = 1,
    ):
        """Construct a CheckResult.

        Args:
            passed: The passed or failed status of the check result.
                If true, indicates that the check has passed.
            description: The description to use in output.
            json_info: The overall information to be included in
                json output.
            path: The path associated with the check result.
            diagnostic: The message to use in output if the check
                has failed.
            weight: The weight of the check result.

        """
        self.passed = passed
        self.description = description
        self.json_info = json_info
        self.diagnostic = diagnostic
        self.path = path
        self.run_command = ""
        self.weight = weight

    def display_result(self, show_diagnostic: bool = False) -> str:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will
        say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if
                the check has failed. Defaults to false.

        """
        icon = "✓" if self.passed else "✕"
        icon_color = "green" if self.passed else "red"
        message = f"[{icon_color}]{icon}[/]  {self.description}"
        if not self.passed and show_diagnostic:
            if "\n" in self.diagnostic:
                message += (
                    f"\n[blue]   → Diagnostic:[/]\n"
                    f"     [yellow]{self.diagnostic}[/]"
                )
            else:
                message += (
                    f"\n[blue]   → Diagnostic:[yellow] {self.diagnostic}[/]"
                )
        return message

    def __repr__(self) -> str:
        """Return a string representation of the CheckResult."""
        return (
            f"CheckResult(passed={self.passed}, "
            f"description='{self.description}', "
            f"json_info={self.json_info}, "
            f"path='{self.path}', "
            f"diagnostic='{self.diagnostic}', "
            f"run_command='{self.run_command}', "
            f"weight={self.weight})"
        )

    def __str__(self, show_diagnostic: bool = False) -> str:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will
        say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if
                the check has failed. Defaults to false.

        """
        message = self.display_result(show_diagnostic)
        return message

    def print(self, show_diagnostic: bool = False) -> None:
        """Print check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will
        say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if
                the check has failed. Defaults to false.

        """
        message = self.display_result(show_diagnostic)
        rich.print(message)
