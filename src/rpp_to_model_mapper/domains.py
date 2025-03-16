from models import *
from rpp_schema_validator import validate_schema

def rpp_to_domain(rpp: dict) -> Domain:
    """Converts a JSON string to a Domain object according to the provided schema."""
    # Create a Domain object from the request body
    domain = Domain(
        name=rpp["name"],
        duration=rpp.get("duration", None),
        registrant=[Registrant(id=x) for x in rpp["registrant"]] if "registrant" in rpp else None,
        authInfo=AuthInfo(pw=rpp["authInfo"].get("pw", None), hash=rpp["authInfo"].get("hash", None)) if "authInfo" in
        rpp else None,
        ns=NS(
            host_objs=[
                HostObj(id=x["name"]) 
                for x in rpp["ns"]["hostObj"]] \
                if "hostObj" in rpp["ns"] else None, 
            host_attrs=[
                HostAttr(id=x["name"], 
                         ipv4=x.get("ipv4", None), 
                         ipv6=x.get("ipv6", None)) 
                for x in rpp["ns"]["hostAttr"]] \
                if "hostAttr" in rpp["ns"] else None) \
            if "ns" in rpp else None,
        contacts=[ContactReference(id=x["value"], types=x["type"]) for x in rpp["contacts"]] if "contacts" in rpp else None,
        dnsSEC=rpp.get("dnsSEC", None)
    )
    return domain

def domain_to_rpp(domain: Domain) -> str:
    """Converts a Domain object to a JSON string according to the provided schema."""

    domain_dict = {}
    domain_dict["name"] = domain.name
    if domain.duration:
        domain_dict["duration"] = domain.duration
    if domain.registrant:
        domain_dict["registrant"] = [registrant.id for registrant in domain.registrant]
    if domain.authInfo:
        domain_dict["authInfo"] = {}
        if domain.authInfo.pw:
            domain_dict["authInfo"]["pw"] = domain.authInfo.pw
        if domain.authInfo.hash:
            domain_dict["authInfo"]["hash"] = domain.authInfo.hash
    if domain.ns:
        ns_dict = {}
        if domain.ns.host_objs:
            ns_dict["host_objs"] = [host_obj.id for host_obj in domain.ns.host_objs]
        if domain.ns.host_attrs:
            ns_dict["host_attrs"] = [{"id": host_attr.id, "ipv4": host_attr.ipv4, "ipv6": host_attr.ipv6} for host_attr in domain.ns.host_attrs]
        if len(ns_dict) > 0:
            domain_dict["ns"] = ns_dict
    if domain.contacts:
        domain_dict["contacts"] = [{"value": contact.id, "type": contact.types} for contact in domain.contacts]
    if domain.dnsSEC:
        domain_dict["dnsSEC"] = domain.dnsSEC
    if domain.status:
        domain_dict["status"] = [x for x in domain.status]
    if domain.crDate:
        domain_dict["crDate"] = domain.crDate
    if domain.exDate:
        domain_dict["exDate"] = domain.exDate
    if domain.upDate:
        domain_dict["upDate"] = domain.upDate
    if domain.trDate:
        domain_dict["trDate"] = domain.trDate
    if domain.clID:
        domain_dict["clID"] = domain.clID
    if domain.crID:
        domain_dict["crID"] = domain.crID

    validate_schema("Domain", domain_dict)
    return domain_dict
