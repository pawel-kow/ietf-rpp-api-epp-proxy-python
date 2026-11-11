from core.model.contact.contacts import ContactMinimal
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domains import ContactReferenceNew, HostObj, NS
from core.model.shared.common import AuthInfo
from core.capabilities.backend_profile import BackendProfile
from rpp.mapping.domain import domain_dns
from rpp.mapping.shared.common import parse_rpp, reject_set
from rpp.mapping.domain.domains import check_contact_label
from core.model.shared.client_statuses import is_client_label
from rpp.dto.rpp_dns_data import RPPDnsData

# Members a client may replace. Any other member of the domain cannot be changed.
CHANGEABLE = ("nameservers", "registrant", "contacts", "status", "dns", "authInfo")
NAMESERVER_RECORDS = ("ns", "a", "aaaa")


def reject_other_changes(current: dict, patched: dict):
    for member in (current.keys() | patched.keys()) - set(CHANGEABLE):
        if current.get(member) != patched.get(member):
            raise ValueError(f"'{member}' cannot be changed")


def _reject_nameservers_with_records(domain: dict):
    """`nameservers` cannot go with the records that delegate (data-objects §11.2). `ds` and `dnskey` can, see spec-issues.md."""
    records = (domain.get("dns") or {}).get("records") or []
    if domain.get("nameservers") and any(str(record.get("type")).lower() in NAMESERVER_RECORDS for record in records):
        raise ValueError("'nameservers' and nameserver records in 'dns' cannot be used together")


def _client_statuses(domain: dict) -> dict[str, str | None]:
    for status in domain.get("status") or []:
        reject_set(due=status.get("due"))
    reasons: dict[str, str | None] = {}
    for status in domain.get("status") or []:
        label, reason = status["label"], status.get("reason") or None
        if is_client_label(label) and (reason or label not in reasons):
            reasons[label] = reason
    return reasons


def _ns(domain_name: str, domain: dict, profile: BackendProfile):
    host_names = [host["hostName"] for host in domain.get("nameservers") or []]
    if not domain.get("dns"):
        attrs, dns_sec = [], None
    else:
        ns, dns_sec = domain_dns.rpp_to_model(domain_name, parse_rpp(RPPDnsData, domain["dns"]), profile=profile)
        attrs = ns.host_attrs if ns else []
    if host_names:
        return NS(host_objs=[HostObj(id=name) for name in host_names], host_attrs=None), dns_sec
    return (NS(host_objs=None, host_attrs=attrs) if attrs else None), dns_sec


def rpp_to_model(
    domain_name: str, domain: dict, auth_info: AuthInfo | None, unchanged: frozenset[str], *, profile: BackendProfile,
) -> DomainReplacement:
    """The replacement a domain representation asks for: a full update, or a read with a patch applied. Its read-only
    members and server statuses are not the client's and are left out. The caller converts `authInfo`, which a read
    need not show, and names the members the request leaves `unchanged`."""
    _reject_nameservers_with_records(domain)
    ns, dns_sec = _ns(domain_name, domain, profile)
    statuses = _client_statuses(domain)
    return DomainReplacement(
        name=domain_name,
        ns=ns,
        registrant=(domain.get("registrant") or {}).get("id"),
        contacts=[
            ContactReferenceNew(type=check_contact_label(contact["label"], profile), contact=ContactMinimal(id=contact["object"]["id"]))
            for contact in domain.get("contacts") or []
        ],
        dnsSEC=dns_sec,
        status=list(statuses),
        status_reasons={label: reason for label, reason in statuses.items() if reason},
        authInfo=auth_info,
        unchanged=unchanged,
    )
