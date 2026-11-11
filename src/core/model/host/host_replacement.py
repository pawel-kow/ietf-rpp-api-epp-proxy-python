from dataclasses import dataclass, field
from typing import Dict, List, Optional


@dataclass(kw_only=True)
class HostReplacement:
    """The wanted state of the members of a host a client may replace. An omitted member is cleared.

    `name` is the name the host has now, `new_name` the one it is to have. `status` holds client statuses only.
    """
    name: str
    new_name: str
    ipv4: Optional[List[str]] = None
    ipv6: Optional[List[str]] = None
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)
