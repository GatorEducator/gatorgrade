"""Define a class of the called ReportParms for the --report tag."""

from enum import Enum


class ReportParamsLocation(str, Enum):
    """Define the location for the parameters of reporting and storing gatorgrade checks."""

    file = "file"
    env = "env"


def validate_location(location):
    """Validate the that there is a value in ReportParamsLocation."""
    if location not in ReportParamsLocation:
        raise ValueError("Invalid location for --report-location: {}".format(location))


class ReportParamsType(str, Enum):
    """Define the type of type to store the data in."""

    json = "json"
    md = "md"


def validate_storing_type(storing_type):
    """Validate the that there is a value in ReportParamsType."""
    if storing_type not in ReportParamsType:
        raise ValueError(
            "Invalid type for --report-storing-type: {}".format(storing_type)
        )


class ReportParamsStoringName(str, Enum):
    """Define the type of type to store the data in."""

    file: str
    github = "github"


def validate_storing_location_name(storing_location_name):
    """Validate the that there is a value in ReportParamsStoringName."""
    if storing_location_name not in ReportParamsStoringName:
        raise ValueError(
            "Invalid type for --report-storing-type: {}".format(storing_location_name)
        )
