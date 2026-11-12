from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class ZoneRecord:
    """A record the registry serves in the zone itself for a domain or a name below it, instead of delegating: an
    address (`a`, `aaaa`) or a mail exchanger (`mx`). Glue, the addresses of a domain's own nameservers, is part of
    its `ns` instead.

    `owner` is the absolute name without the trailing dot, in lowercase.
    """
    owner: str
    type: str
    address: Optional[str] = None
    preference: Optional[int] = None
    exchange: Optional[str] = None
