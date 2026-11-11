from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class DomainIdn:
    """The IDN data of a domain: the label generation ruleset (LGR) of its name and the Unicode form of the name."""
    lgr: str
    uname: Optional[str] = None
