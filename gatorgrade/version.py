"""Single source of truth for the gatorgrade version number.

This module exists so that both gatorgrade.main and
gatorgrade.hint.remote_engine can import the version without
creating a circular dependency.  The value must always match
the version in pyproject.toml.

Use it anywhere you need the version string:

    from gatorgrade.version import GATORGRADE_VERSION
"""

GATORGRADE_VERSION = "0.11.0"
