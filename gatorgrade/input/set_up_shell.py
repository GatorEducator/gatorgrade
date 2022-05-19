"""Set-up the shell commands."""
import subprocess
import sys


def run_setup(front_matter):
    """Run the shell set up commands and exit the program if a command fails.

    Args:
        front_matter: A dictionary whose 'setup' key contains the set up commands
        as a multi-line string.

    """
    # If setup exists in the front matter
    setup = front_matter.get("setup")
    if setup:
        print("Running set up commands...")
        for line in setup.splitlines():
            # Trims the white space
            command = line.strip()
            # Executes the command
            proc = subprocess.run(command, shell=True, check=False, timeout=300)
            # If the exit code tells it was unsuccessful and did not return 0
            if proc.returncode != 0:
                print(
                    f'The set up command "{command}" failed.\
                Exiting GatorGrade.',
                    file=sys.stderr,
                )
                # If a set up command failed, exit the execution
                # because environment was not set up correctly.
                sys.exit(1)
        print("Finished!\n")
