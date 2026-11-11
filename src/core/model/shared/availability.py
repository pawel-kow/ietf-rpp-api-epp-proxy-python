from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class Availability:
    """Whether an object of the name can be created, and why not when it cannot."""
    name: str
    available: bool
    reason: Optional[str] = None
