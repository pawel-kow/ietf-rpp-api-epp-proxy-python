from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domains import ContactReference, CreationProcess, Domain, HostObj, NS
from core.capabilities.backend_profile import BackendProfile
from rpp.schema.validator import validate_schema
from rpp.mapping.domain import domain_dns
from rpp.mapping.shared import auth_info, prov_metadata, statuses
from rpp.mapping.shared.common import parse_rpp, period_duration, reject_set
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from rpp.dto.rpp_contact_reference import RPPContactReference
from rpp.dto.rpp_domain import RPPDomain
from rpp.dto.rpp_host_reference import RPPHostReference
from rpp.dto.rpp_labelled_contact import RPPLabelledContact

REGISTRANT = "registrant"


def check_contact_label(label: str, profile: BackendProfile) -> str:
    """The RPP label is open, the backend knows a fixed set of contact roles."""
    if label not in profile.contact_labels:
        raise NotSupportedByBackend(f"Contact label '{label}'")
    return label


def _rpp_to_contacts(domain_rpp: RPPDomain, profile: BackendProfile) -> list[ContactReference] | None:
    contacts = []
    if domain_rpp.registrant is not None:
        contacts.append(ContactReference(id=domain_rpp.registrant.id, types=[REGISTRANT]))
    for contact in domain_rpp.contacts or []:
        contacts.append(ContactReference(id=contact.object.id, types=[check_contact_label(contact.label, profile)]))
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
    return {"creation": CreationProcess(duration=period_duration(period))}


def _rpp_to_delegation(domain_rpp: RPPDomain, profile: BackendProfile) -> tuple[NS | None, DnsSec | None]:
    ns = None
    if domain_rpp.nameservers:
        ns = NS(host_objs=[HostObj(id=h.hostName) for h in domain_rpp.nameservers], host_attrs=None)
    if domain_rpp.dns is None:
        return ns, None
    if ns and domain_rpp.dns.records:
        raise ValueError("'nameservers' and records in 'dns' cannot be used together")
    dns_ns, dns_sec = domain_dns.rpp_to_model(domain_rpp.name, domain_rpp.dns, profile=profile)
    return ns or dns_ns, dns_sec


def _rpp_to_idn(domain_rpp: RPPDomain, profile: BackendProfile) -> DomainIdn | None:
    """The `lgr` must be one the backend offers. Json §6.4 requires it whenever `uName` is given."""
    if domain_rpp.lgr is None:
        if domain_rpp.uName is not None:
            raise ValueError("'uName' needs 'lgr'")
        return None
    if domain_rpp.lgr not in profile.lgrs:
        raise ValueError(f"The LGR '{domain_rpp.lgr}' is not offered")
    return DomainIdn(lgr=domain_rpp.lgr, uname=domain_rpp.uName)


def rpp_to_model(rpp: dict, *, profile: BackendProfile) -> Domain:
    """Converts a create request to a Domain, with what the backend of `profile` can hold."""
    validate_schema("domainName.create", rpp)
    domain_rpp = parse_rpp(RPPDomain, rpp)
    reject_set(status=domain_rpp.status)
    ns, dns_sec = _rpp_to_delegation(domain_rpp, profile)
    return Domain(
        name=domain_rpp.name,
        authInfo=auth_info.rpp_to_model(domain_rpp.authInfo),
        ns=ns,
        dnsSEC=dns_sec,
        contacts=_rpp_to_contacts(domain_rpp, profile),
        processes=_rpp_to_processes(domain_rpp),
        idn=_rpp_to_idn(domain_rpp, profile),
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


def _idn_to_rpp(domain: Domain) -> tuple[str | None, str | None]:
    """The `uName` and `lgr` of a domain."""
    if domain.idn is None:
        return None, None
    return domain.idn.uname, domain.idn.lgr


def model_to_rpp(domain: Domain) -> dict:
    """Converts a Domain to its read representation."""
    u_name, lgr = _idn_to_rpp(domain)
    domain_dict = RPPDomain(
        name=domain.name,
        uName=u_name,
        lgr=lgr,
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
