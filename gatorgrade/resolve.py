"""Configuration file resolution utilities for GatorGrade.

Provides functions that resolve system prompt files and validation
rules files specified in the gatorgrade YAML configuration front
matter. Resolution follows a search order: current working directory,
alongside the configuration file, then the config directory.
"""

import json
from pathlib import Path
from typing import Optional

from gatorgrade.input.parse_config import (
    get_config_dir,
    get_system_prompt_file,
    get_validation_phrases_file,
)


def resolve_system_prompt(
    config_path: Path, config_dir: Optional[Path]
) -> Optional[str]:
    """Read the system prompt file if specified in the config front matter.

    The filename is read from the system_prompt_file field in
    the YAML front matter, then resolved in this search order:

    1. Current working directory
    2. Alongside the configuration file itself
    3. The --config-dir directory (or the default platformdirs-
       based config directory)

    Args:
        config_path: Path to the resolved gatorgrade configuration
            file.
        config_dir: The config directory (from --config-dir),
            or None to use the default.

    Returns:
        The contents of the system prompt file, or None if not
        specified or not found.

    """
    prompt_filename = get_system_prompt_file(config_path)
    if not prompt_filename:
        return None
    # search order: cwd, alongside config file, config dir
    for candidate in [
        Path(prompt_filename),
        config_path.parent / prompt_filename,
        (config_dir or get_config_dir()) / prompt_filename,
    ]:
        if candidate.exists():
            try:
                return candidate.read_text(encoding="utf-8")
            except OSError:
                return None
    return None


def resolve_validation_rules(
    config_path: Path, config_dir: Optional[Path]
) -> dict[str, list[str]] | None:
    """Read the validation rules JSON file if specified in the config front matter.

    The filename is read from the validation_phrases_file field
    in the YAML front matter. The JSON file must contain an object
    with optional keys:

    - must_contain: list of phrases that must appear in hints
    - cannot_contain: list of phrases that must not appear

    The file is resolved in the same search order as the system
    prompt: CWD, alongside config file, then config dir.

    Args:
        config_path: Path to the resolved gatorgrade configuration
            file.
        config_dir: The config directory (from --config-dir),
            or None to use the default.

    Returns:
        The parsed validation rules dict, or None if not specified
        or not found.

    """
    filename = get_validation_phrases_file(config_path)
    if not filename:
        return None
    for candidate in [
        Path(filename),
        config_path.parent / filename,
        (config_dir or get_config_dir()) / filename,
    ]:
        if candidate.exists():
            try:
                data = json.loads(candidate.read_text(encoding="utf-8"))
                if not isinstance(data, dict):
                    return None
                return data
            except (json.JSONDecodeError, OSError):
                return None
    return None
