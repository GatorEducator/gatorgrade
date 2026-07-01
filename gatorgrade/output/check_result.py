"""Define check result class."""

from typing import Any, Dict, Optional, Union

import rich

NEWLINE = "\n"
EMPTY = ""
CHECK_MARK = "\u2713"
CROSS_MARK = "\u2715"
PASS_COLOR = "green"
FAIL_COLOR = "red"
DIAGNOSTIC_LABEL = "Diagnostic"
HINT_LABEL = "Hint"


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
        outputlimit: int | None = None,
        hint: str | None = None,
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
            outputlimit: The maximum number of diagnostic lines
                displayed for this check.
            hint: An optional hint shown when the check fails.

        """
        self.passed = passed
        self.description = description
        self.json_info = json_info
        self.diagnostic = diagnostic
        self.path = path
        self.run_command = EMPTY
        self.weight = weight
        self.outputlimit = outputlimit
        self.hint = hint

    def display_result(self, show_diagnostic: bool = False) -> str:
        """Return check's passed or failed status, description, and, optionally, diagnostic message.

        If no diagnostic message is available, then the output will
        say so.

        Args:
            show_diagnostic: If true, show the diagnostic message if
                the check has failed. Defaults to false.

        """
        icon = CHECK_MARK if self.passed else CROSS_MARK
        icon_color = PASS_COLOR if self.passed else FAIL_COLOR
        message = f"[{icon_color}]{icon}[/]  {self.description}"
        if not self.passed and show_diagnostic:
            if NEWLINE in self.diagnostic:
                message += (
                    f"\n[blue]   → {DIAGNOSTIC_LABEL}:[/]\n"
                    f"     [yellow]{self.diagnostic}[/]"
                )
            else:
                message += f"\n[blue]   → {DIAGNOSTIC_LABEL}:[yellow] {self.diagnostic}[/]"
            if self.hint:
                message += f"\n[blue]   → {HINT_LABEL}:[green] {self.hint}[/]"
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
            f"weight={self.weight}, "
            f"outputlimit={self.outputlimit})"
        )

    def __str__(self) -> str:
        """Return check's passed or failed status and description.

        Does not include diagnostic details. Use display_result() or
        print() with show_diagnostic=True to see diagnostic output.

        """
        return self.display_result()

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
