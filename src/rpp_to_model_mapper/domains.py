from models import (
    ContactReference, CreationProcess, DnsSec, Domain, HostObj, NS,
)
from rpp_schema_validator import validate_schema
from . import auth_info, domain_dns, prov_metadata, statuses
from .common import parse_rpp, reject_set
from .not_supported_by_epp import NotSupportedByEpp
from .rpp_models import RPPContactReference, RPPDomain, RPPHostReference, RPPLabelledContact

REGISTRANT = "registrant"
CONTACT_LABELS = ("admin", "billing", "tech")


def check_contact_label(label: str) -> str:
    """EPP knows three contact roles, the RPP label is open."""
    if label not in CONTACT_LABELS:
        raise NotSupportedByEpp(f"Contact label '{label}'")
    return label


def _rpp_to_contacts(domain_rpp: RPPDomain) -> list[ContactReference] | None:
    contacts = []
    if domain_rpp.registrant is not None:
        contacts.append(ContactReference(id=domain_rpp.registrant.id, types=[REGISTRANT]))
    for contact in domain_rpp.contacts or []:
        contacts.append(ContactReference(id=contact.object.id, types=[check_contact_label(contact.label)]))
    return contacts or None


def _rpp_to_processes(domain_rpp: RPPDomain) -> dict | None:
    create_processes = domain_rpp.processes.createProcess if domain_rpp.processes else None
    if not create_processes:
        return None
    if len(create_processes) > 1:
        raise ValueError("Only one createProcess is allowed in a create request")
    period = create_processes[0].period
    if period is None:
        return None
    return {"creation": CreationProcess(duration=f"P{period.value}{period.unit.upper()}")}


def _rpp_to_delegation(domain_rpp: RPPDomain) -> tuple[NS | None, DnsSec | None]:
    ns = None
    if domain_rpp.nameservers:
        ns = NS(host_objs=[HostObj(id=h.hostName) for h in domain_rpp.nameservers], host_attrs=None)
    if domain_rpp.dns is None:
        return ns, None
    if ns and domain_rpp.dns.records:
        raise ValueError("'nameservers' and records in 'dns' cannot be used together")
    dns_ns, dns_sec = domain_dns.rpp_to_model(domain_rpp.name, domain_rpp.dns)
    return ns or dns_ns, dns_sec


def rpp_to_model(rpp: dict) -> Domain:
    """Converts a create request to a Domain."""
    validate_schema("domainName.create", rpp)
    domain_rpp = parse_rpp(RPPDomain, rpp)
    reject_set(status=domain_rpp.status, uName=domain_rpp.uName, lgr=domain_rpp.lgr)
    ns, dns_sec = _rpp_to_delegation(domain_rpp)
    return Domain(
        name=domain_rpp.name,
        authInfo=auth_info.rpp_to_model(domain_rpp.authInfo),
        ns=ns,
        dnsSEC=dns_sec,
        contacts=_rpp_to_contacts(domain_rpp),
        processes=_rpp_to_processes(domain_rpp),
    )


def _nameservers_to_rpp(domain: Domain) -> list[RPPHostReference] | None:
    if domain.ns is None:
        return None
    return [RPPHostReference(hostName=host.id) for host in domain.ns.host_objs or []] or None


def _registrant_to_rpp(domain: Domain) -> RPPContactReference | None:
    for contact in domain.contacts or []:
        if REGISTRANT in contact.types:
            return RPPContactReference(id=contact.id)
    return None


def _contacts_to_rpp(domain: Domain) -> list[RPPLabelledContact] | None:
    return [
        RPPLabelledContact(label=label, object=RPPContactReference(id=contact.id))
        for contact in domain.contacts or []
        for label in contact.types
        if label != REGISTRANT
    ] or None


def model_to_rpp(domain: Domain) -> dict:
    """Converts a Domain to its read representation."""
    domain_dict = RPPDomain(
        name=domain.name,
        provMetadata=prov_metadata.model_to_rpp(domain),
        status=statuses.model_to_rpp(domain, "domainStatus"),
        registrant=_registrant_to_rpp(domain),
        contacts=_contacts_to_rpp(domain),
        nameservers=_nameservers_to_rpp(domain),
        dns=domain_dns.model_to_rpp(domain),
        subordinateHosts=[RPPHostReference(hostName=name) for name in domain.subordinateHosts or []] or None,
        expiryDate=domain.exDate,
        authInfo=auth_info.model_to_rpp(domain.authInfo),
    ).to_rpp()
    validate_schema("domainName.read", domain_dict)
    return domain_dict
