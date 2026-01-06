from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class GatorCheck(BaseModel):
    description: str = Field(..., min_length=1)
    check: str
    options: Optional[Dict[str, Any]] = None

class GatorConfig(BaseModel):
    """Allowing the YAML to be a list of GatorCheck objects."""
    check: List[GatorCheck]

