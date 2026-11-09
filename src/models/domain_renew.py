from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class DomainRenew:
    """A renewal of a domain. `curExpDate` is the current expiry as a date (EPP holds no time)."""
    name: str
    curExpDate: Optional[str] = None
    duration: Optional[str] = None
