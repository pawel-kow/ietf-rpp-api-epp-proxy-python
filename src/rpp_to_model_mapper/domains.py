from models import *

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
                HostObj(id=x) 
                for x in rpp["ns"]["host_objs"]] \
                if "host_objs" in rpp["ns"] else None, 
            host_attrs=[
                HostAttr(id=x["id"], 
                         ipv4=x.get("ipv4", None), 
                         ipv6=x.get("ipv6", None)) 
                for x in rpp["ns"]["host_attrs"]] \
                if "host_attrs" in rpp["ns"] else None) \
            if "ns" in rpp else None,
        contacts=rpp.get("contacts", None),
        dnsSEC=rpp.get("dnsSEC", None)
    )
    return domain

def domain_to_rpp(domain: Domain) -> str:
    """Converts a Domain object to a JSON string according to the provided schema."""

    domain_dict = {
        "name": domain.name,
        "duration": domain.duration,
        "registrant": [registrant.id for registrant in domain.registrant],
        "authInfo": {
            "pw": domain.authInfo.pw,
            "hash": domain.authInfo.hash,
        } if domain.authInfo else None,
        "ns": {
            "host_objs": [host_obj.id for host_obj in domain.ns.host_objs] if domain.ns.host_objs else None,
            "host_attrs": [{"id": host_attr.id, "ipv4": host_attr.ipv4, "ipv6": host_attr.ipv6} for host_attr in domain.ns.host_attrs] if domain.ns.host_attrs else None,
        } if domain.ns else
        None,
        "contacts": [{"id": contact.id} for contact in domain.contacts],
        "dnsSEC": domain.dnsSEC,
        "status": [x for x in domain.status],
    }

    return domain_dict