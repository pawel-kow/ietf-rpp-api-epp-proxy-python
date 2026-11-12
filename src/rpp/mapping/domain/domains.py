from core.capabilities.backend_profile import BackendProfile
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domains import ContactReference, CreationProcess, Domain, HostObj, NS
from core.model.domain.zone_record import ZoneRecord
from rpp.dto.rpp_contact_reference import RPPContactReference
from rpp.dto.rpp_domain import RPPDomain
from rpp.dto.rpp_host_reference import RPPHostReference
from rpp.dto.rpp_labelled_contact import RPPLabelledContact
from rpp.mapping.domain import domain_dns
from rpp.mapping.shared import auth_info, prov_metadata, statuses
from rpp.mapping.shared.common import parse_rpp, period_duration, reject_set
from rpp.schema.validator import validate_schema

REGISTRANT = "registrant"


def check_contact_label(label: str, profile: BackendProfile) -> str:
    """The RPP label is open, the backend knows a fixed set of contact roles. A backend that holds several
    registrants takes the ones after `registrant` as contacts labelled `registrant`."""
    if label == REGISTRANT and profile.max_registrants > 1:
        return label
    if label not in profile.contact_labels:
        raise NotSupportedByBackend(f"Contact label '{label}'")
    return label


def check_host_objects(host_names: list, profile: BackendProfile):
    """`nameservers` are host objects, which a backend without them (`profile.host_objects`) cannot hold: it takes
    name servers as `ns` records in `dns` (gap Q12)."""
    if host_names and not profile.host_objects:
        raise NotSupportedByBackend("'nameservers' (host objects)")


def check_client_statuses(labels, profile: BackendProfile):
    """A backend whose statuses are all its own (`profile.client_statuses`) takes none from a client."""
    if labels and not profile.client_statuses:
        raise NotSupportedByBackend(f"Client status '{next(iter(labels))}'")


def check_registrants(registrants: int, profile: BackendProfile):
    if registrants > profile.max_registrants:
        raise NotSupportedByBackend(f"More than {profile.max_registrants} registrants")


def check_requested(requested: frozenset[str], *, profile: BackendProfile) -> frozenset[str]:
    """The data elements a request asks to include, refused where the backend never shows one: a backend that cannot
    read back a domain's authInfo (`profile.auth_info_readable`) refuses `includeElements=authInfo` rather than let a
    client take its absence for no authInfo."""
    if "authInfo" in requested and not profile.auth_info_readable:
        raise NotSupportedByBackend("Reading the 'authInfo' of a domain")
    return requested


def _rpp_to_contacts(domain_rpp: RPPDomain, profile: BackendProfile) -> list[ContactReference] | None:
    contacts = []
    if domain_rpp.registrant is not None:
        contacts.append(ContactReference(id=domain_rpp.registrant.id, types=[REGISTRANT]))
    for contact in domain_rpp.contacts or []:
        contacts.append(ContactReference(id=contact.object.id, types=[check_contact_label(contact.label, profile)]))
    check_registrants(sum(REGISTRANT in contact.types for contact in contacts), profile)
    return contacts or None


def _rpp_to_processes(domain_rpp: RPPDomain, profile: BackendProfile) -> dict | None:
    create_processes = domain_rpp.processes.createProcess if domain_rpp.processes else None
    if not create_processes:
        return None
    if len(create_processes) > 1:
        raise ValueError("Only one createProcess is allowed in a create request")
    period = create_processes[0].period
    if period is None:
        return None
    if not profile.registration_periods:
        raise NotSupportedByBackend("A registration period")
    return {"creation": CreationProcess(duration=period_duration(period))}


def _rpp_to_delegation(domain_rpp: RPPDomain, profile: BackendProfile
                       ) -> tuple[NS | None, DnsSec | None, list[ZoneRecord]]:
    ns = None
    check_host_objects(domain_rpp.nameservers, profile)
    if domain_rpp.nameservers:
        ns = NS(host_objs=[HostObj(id=h.hostName) for h in domain_rpp.nameservers], host_attrs=None)
    if domain_rpp.dns is None:
        return ns, None, []
    if ns and domain_rpp.dns.records:
        raise ValueError("'nameservers' and records in 'dns' cannot be used together")
    dns_ns, dns_sec, records = domain_dns.rpp_to_model(domain_rpp.name, domain_rpp.dns, profile=profile)
    return ns or dns_ns, dns_sec, records


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
    ns, dns_sec, records = _rpp_to_delegation(domain_rpp, profile)
    return Domain(
        name=domain_rpp.name,
        authInfo=auth_info.rpp_to_model(domain_rpp.authInfo),
        ns=ns,
        dnsSEC=dns_sec,
        records=records or None,
        contacts=_rpp_to_contacts(domain_rpp, profile),
        processes=_rpp_to_processes(domain_rpp, profile),
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
    """The contacts other than the first registrant, which is `registrant`: further registrants are labelled so."""
    contacts, first = [], True
    for contact in domain.contacts or []:
        for label in contact.types:
            if label == REGISTRANT and first:
                first = False
                continue
            contacts.append(RPPLabelledContact(label=label, object=RPPContactReference(id=contact.id)))
    return contacts or None


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
