"""Set-up the shell commands."""
import os, sys


def run_setup(front_matter):
    """Run the shell set up commands and exit the program if a command fails.
    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.
    """
    print("Running set up commands...")
    for line in front_matter["setup"].splitlines():
        # Trims the white space
        command = line.strip()
        exit_status = os.system(command)
        # Extracts the exit code number from the exit status.
        exit_code = os.WEXITSTATUS(exit_status)
        if exit_code != 0:
            print(
                f'The set up command "{command}" failed.\
            Exiting GatorGrader.',
                file=sys.stderr,
            )
            # If a set up command failed, exit the execution
            # because environment was not set up correctly.
            sys.exit()
