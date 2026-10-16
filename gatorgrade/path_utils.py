from pathlib import Path
from typing import Union

def to_filesystem_path(path_input: Union[str, Path]) -> Path:
    """Converts string or Path objects into an OS-native Path."""
    return Path(path_input).expanduser().resolve()
