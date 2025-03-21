from dataclasses import dataclass, field
from typing import List, Optional, Dict

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
    types: List[str]
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
class Process:
    pass

class CreationProcess(Process):
    duration: str

@dataclass
class Domain:
    name: str
    status: Optional[List[str]] = None
    authInfo: Optional[AuthInfo] = None
    ns: NS = None
    contacts: Optional[List[ContactReference]] = None
    dnsSEC: Optional[List[DnsSec]] = None
    crDate: Optional[str] = None
    exDate: Optional[str] = None
    upDate: Optional[str] = None
    trDate: Optional[str] = None
    clID: Optional[str] = None
    crID: Optional[str] = None
    processes: Dict[str, Process] = None
    
    def update(self, domain):
        self.name = domain.name if domain.name else self.name
        self.processes = domain.processes if domain.processes else self.processes
        self.status = domain.status if domain.status and len(domain.status) > 0 else self.status
        self.authInfo = domain.authInfo if domain.authInfo else self.authInfo
        # TODO: cascade update
        self.ns = domain.ns if domain.ns and (domain.ns.host_objs and len(domain.ns.host_objs) > 0 or domain.ns.host_attrs and len(domain.ns.host_attrs) > 0) else self.ns
        # TODO: cascade update
        self.contacts = domain.contacts if domain.contacts else self.contacts
        # TODO: cascade update
        self.dnsSEC = domain.dnsSEC if domain.dnsSEC else self.dnsSEC
        self.crDate = domain.crDate if domain.crDate else self.crDate
        self.exDate = domain.exDate if domain.exDate else self.exDate
        self.upDate = domain.upDate if domain.upDate else self.upDate
        self.trDate = domain.trDate if domain.trDate else self.trDate
        self.clID = domain.clID if domain.clID else self.clID
        self.crID = domain.crID if domain.crID else self.crID

@dataclass
class DomainCreateResponse:
    domain: Domain
    server_transaction_id: str
    
@dataclass
class DomainInfoResponse:
    domain: Domain
    server_transaction_id: str