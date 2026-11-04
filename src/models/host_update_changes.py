from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(kw_only=True)
class HostUpdateChanges:
    """What a host update adds to or removes from the host."""
    ipv4: List[str] = field(default_factory=list)
    ipv6: List[str] = field(default_factory=list)
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.ipv4 or self.ipv6 or self.status)
