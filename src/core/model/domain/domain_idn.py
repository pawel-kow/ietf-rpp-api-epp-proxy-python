from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class DomainIdn:
    """The IDN data of a domain: the registry's IDN table and the Unicode form of the name."""
    table: str
    uname: Optional[str] = None
