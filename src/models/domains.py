from dataclasses import dataclass, field
from typing import List, Optional, Dict
from .common import Process, ProvisioningObject
from .response import OperationResponse

@dataclass(kw_only=True)
class HostObj:
    id: str

@dataclass(kw_only=True)
class HostAttr:
    id: str
    ipv4: Optional[str] = None
    ipv6: Optional[str] = None

@dataclass(kw_only=True)
class NS:
    host_objs: Optional[List[HostObj]]
    host_attrs: Optional[List[HostAttr]]

@dataclass(kw_only=True)
class ContactReference:
    types: List[str]
    id: str

@dataclass(kw_only=True)
class DnsSec:
    # Add DNSSEC properties here if needed
    pass

@dataclass(kw_only=True)
class CreationProcess(Process):
    duration: str

@dataclass(kw_only=True)
class Domain(ProvisioningObject):
    name: str
    ns: Optional[NS] = None
    contacts: Optional[List[ContactReference]] = None
    dnsSEC: Optional[List[DnsSec]] = None
    processes: Optional[Dict[str, Process]] = None
    
    def update(self, obj):
        super().update(obj)

        self.name = obj.name if obj.name else self.name
        self.processes = obj.processes if obj.processes else self.processes
        # TODO: cascade update
        self.ns = obj.ns if obj.ns and (obj.ns.host_objs and len(obj.ns.host_objs) > 0 or obj.ns.host_attrs and len(obj.ns.host_attrs) > 0) else self.ns
        # TODO: cascade update
        self.contacts = obj.contacts if obj.contacts else self.contacts
        # TODO: cascade update
        self.dnsSEC = obj.dnsSEC if obj.dnsSEC else self.dnsSEC


@dataclass(kw_only=True)
class DomainCreateResponse(OperationResponse):
    domain: Domain

@dataclass(kw_only=True)
class DomainCheckResponseSingle(OperationResponse):
    domain_name: str
    available: bool
    reason: str

@dataclass(kw_only=True)
class DomainCheckResponseBulk(OperationResponse):
    responses: dict[str, DomainCheckResponseSingle]

@dataclass(kw_only=True)
class DomainInfoResponse(OperationResponse):
    domain: Domain

@dataclass(kw_only=True)
class DomainDeleteResponse(OperationResponse):
    pass
