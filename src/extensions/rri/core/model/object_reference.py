from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class ObjectReference:
    """An object a registry message is about: its type (`domainName`, `contact`) and identifier, and the date that concerns it
    where the message has one (the expiry of a domain name, a verification deadline)."""
    object_type: str
    object_id: str
    date: Optional[str] = None
