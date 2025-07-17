from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .common import Process, ProvisioningObject
from .response import OperationResponse

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

class CreationProcess(Process):
    duration: str

@dataclass(kw_only=True)
class Domain(ProvisioningObject):
    name: str
    status: Optional[List[str]] = None
    authInfo: Optional[AuthInfo] = None
    ns: NS = None
    contacts: Optional[List[ContactReference]] = None
    dnsSEC: Optional[List[DnsSec]] = None
    processes: Dict[str, Process] = None
    
    def update(self, domain):
        super().update(domain)

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


@dataclass
class DomainCreateResponse(OperationResponse):
    domain: Domain

@dataclass
class DomainInfoResponse(OperationResponse):
    domain: Domain

@dataclass
class DomainDeleteResponse(OperationResponse):
    pass
