from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Registrant:
    id: str

@dataclass
class HostObj:
    id: str
    pass

@dataclass
class HostAttr:
    id: str
    ipv4: str
    ipv6: str

@dataclass
class NS:
    host_objs: Optional[List[HostObj]]
    host_attrs: Optional[List[HostAttr]]

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
    status: Optional[List[str]] = None
    registrant: List[Registrant] = field(default_factory=list)
    authInfo: Optional[AuthInfo] = None
    ns: NS = None
    contacts: List[ContactReference] = field(default_factory=list)
    dnsSEC: List[DnsSec] = field(default_factory=list)
    crDate: Optional[str] = None
    exDate: Optional[str] = None
    upDate: Optional[str] = None
    trDate: Optional[str] = None
    clID: Optional[str] = None # element that contains the identifier of the sponsoring client.
    crID: Optional[str] = None #element that contains the identifier of the client that created the domain object.
    
@dataclass
class DomainCreateResponse:
    domain: Domain
    server_transaction_id: str