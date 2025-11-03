from models import *
from .rpp_models import *
from rpp_schema_validator import validate_schema
from .common import provisioning_object_to_rpp

def rpp_to_domain(rpp: dict) -> Domain:
    """Converts a JSON string to a Domain object according to the provided schema."""
    # First validate the schema
    validate_schema("Domain", rpp)
    domain_rpp = RPPDomain.from_dict(rpp) # type: ignore
    # Create a Domain object from the request body
    domain = Domain(
        name=domain_rpp.name,
        authInfo=AuthInfo(pw=domain_rpp.authInfo.pw, hash=domain_rpp.authInfo.hash) if domain_rpp.authInfo is not None else None,
        ns=NS(
            host_objs=[
                HostObj(id=x["name"]) 
                for x in rpp["ns"]["hostObj"]] \
                if "hostObj" in rpp["ns"] else None, 
            host_attrs=[
                HostAttr(id=x["name"], 
                         ipv4=x["addr"].get("ipv4", None) if "addr" in x else None, 
                         ipv6=x["addr"].get("ipv6", None)  if "addr" in x else None) 
                for x in rpp["ns"]["hostAttr"]] \
                if "hostAttr" in rpp["ns"] else None) \
            if "ns" in rpp else None,
        contacts=[ContactReference(id=x["value"], types=x["type"]) for x in rpp["contacts"]] if "contacts" in rpp else None,
        dnsSEC=rpp.get("dnsSEC", None)
    )
    if "processes" in rpp:
        domain.processes = {}
        for process_name, process in rpp["processes"].items():
            if process_name == "creation":
                domain.processes[process_name] = CreationProcess(duration=process["period"])
            else:
                domain.processes[process_name] = Process()
    return domain

def domain_to_rpp(domain: Domain) -> dict:
    """Converts a Domain object to a JSON string according to the provided schema."""

    domain_dict = {}
    domain_dict["name"] = domain.name
    if domain.ns:
        ns_dict = {}
        if domain.ns.host_objs:
            ns_dict["hostObj"] = [{"name": host_obj.id} for host_obj in domain.ns.host_objs]
        if domain.ns.host_attrs:
            ns_dict["hostAttr"] = [{"name": host_attr.id, "ipv4": host_attr.ipv4, "ipv6": host_attr.ipv6} for host_attr in domain.ns.host_attrs]
        if len(ns_dict) > 0:
            domain_dict["ns"] = ns_dict
    if domain.contacts:
        domain_dict["contacts"] = [{"value": contact.id, "type": contact.types} for contact in domain.contacts]
    if domain.dnsSEC:
        domain_dict["dnsSEC"] = domain.dnsSEC

    provisioning_object_to_rpp(domain, domain_dict)

    validate_schema("Domain", domain_dict)
    return domain_dict

def rpp_to_domain_update(domain_name: str, rpp: dict) -> DomainUpdate:
    """Converts a JSON string to a DomainUpdate object according to the provided schema."""
    # First validate the schema
    validate_schema("DomainUpdateModel", rpp)
    domain_rpp_update = RPPDomainUpdate.from_dict(rpp) # type: ignore
    
    return DomainUpdate(
        name=domain_name,
        add=DomainUpdateAdd(
            ns=rpp_hosts_to_hosts(domain_rpp_update.add.ns) if domain_rpp_update.add.ns is not None else None,
            contacts=rpp_contacts_to_contact_references(domain_rpp_update.add.contacts) if domain_rpp_update.add.contacts is not None else None
            # TODO: dnsSEC
        ) if domain_rpp_update.add is not None else None,
        remove=DomainUpdateRemove(
            ns=rpp_hosts_to_hosts(domain_rpp_update.remove.ns) if domain_rpp_update.remove.ns is not None else None,
            contacts=rpp_contacts_to_contact_references(domain_rpp_update.remove.contacts) if domain_rpp_update.remove.contacts is not None else None
            # TODO: dnsSEC
        ) if domain_rpp_update.remove is not None else None,
        change=DomainUpdateChange(
            authInfo=AuthInfo(
                pw=domain_rpp_update.update.authInfo.pw,
                hash=domain_rpp_update.update.authInfo.hash
            ) if domain_rpp_update.update.authInfo is not None else None
        ) if domain_rpp_update.update is not None else None
    )
    
def rpp_hosts_to_hosts(rpp_hosts: RPPNS) -> NS:
    return NS(
        host_attrs = [
            HostAttr(
                id=host_attr.name,
                ipv4=[ip for ip in host_attr.ipv4] if host_attr.ipv4 else None,
                ipv6=[ip for ip in host_attr.ipv6] if host_attr.ipv6 else None
            ) for host_attr in rpp_hosts.hostAttrs
        ] if rpp_hosts.hostAttrs else None,
        host_objs = [
            HostObj(
                id=host_obj.name
            ) for host_obj in rpp_hosts.hostObj
        ] if rpp_hosts.hostObj else None
    )

def rpp_contacts_to_contact_references(rpp_contacts: List[RPPContactReferenceNew]) -> List[ContactReferenceNew]:
    return [
        ContactReferenceNew(
            type=contact.type,
            contact=ContactMinimal(id=contact.object.id)
        ) for contact in rpp_contacts
    ]