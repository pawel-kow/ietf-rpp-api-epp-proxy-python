from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Registrant:
    id: str

@dataclass
class HostInfo:
    # Add host info properties here if needed
    pass

@dataclass
class ContactReference:
    id: str

@dataclass
class DnsSec:
    # Add DNSSEC properties here if needed
    pass

@dataclass
class AuthInfo:
    pw: str
    hash: str

@dataclass
class Domain:
    name: str
    duration: Optional[str] = None
    registrant: List[Registrant] = field(default_factory=list)
    authInfo: Optional[AuthInfo] = None
    ns: Optional[dict] = None # ns will contain hostObj and hostAttr lists
    contacts: List[ContactReference] = field(default_factory=list)
    dnsSEC: List[DnsSec] = field(default_factory=list)