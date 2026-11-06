from models import (
    ContactMinimal, ContactReferenceNew, DnsSec, DomainUpdate, DomainUpdateAdd, DomainUpdateRemove, HostAttr, HostObj, NS,
)
from . import domain_dns
from .common import parse_rpp
from .domains import REGISTRANT, check_contact_label
from .not_supported_by_proxy import NotSupportedByProxy
from .rpp_models import RPPDnsData

CLIENT_STATUS_PREFIX = "client"
# Members the difference turns into EPP. Any other member of the object cannot be changed.
CHANGEABLE = ("nameservers", "registrant", "contacts", "status", "dns", "authInfo")


def _reject_other_changes(current: dict, patched: dict):
    for member in (current.keys() | patched.keys()) - set(CHANGEABLE):
        if current.get(member) != patched.get(member):
            raise ValueError(f"'{member}' cannot be changed")


def _missing_from(values: list, others: list, key=lambda value: value) -> list:
    """The values whose key is not among the others, in their order and without repeats."""
    known = {key(other) for other in others}
    missing = []
    for value in values:
        if key(value) not in known:
            known.add(key(value))
            missing.append(value)
    return missing


def _host_names(domain: dict) -> list[str]:
    return [host["hostName"] for host in domain.get("nameservers") or []]


def _contact_pairs(domain: dict) -> list[tuple[str, str]]:
    return [(check_contact_label(contact["label"]), contact["object"]["id"]) for contact in domain.get("contacts") or []]


def _references(pairs: list[tuple[str, str]]) -> list[ContactReferenceNew] | None:
    return [ContactReferenceNew(type=label, contact=ContactMinimal(id=contact_id)) for label, contact_id in pairs] or None


def _pair_key(pair: tuple[str, str]) -> tuple[str, str]:
    return pair[0], pair[1].lower()


def _registrant(domain: dict) -> str | None:
    return (domain.get("registrant") or {}).get("id")


def _delegation(domain: dict) -> tuple[list[HostAttr], DnsSec | None]:
    """The host attributes and DNSSEC data of the records of `dns`."""
    if not domain.get("dns"):
        return [], None
    ns, dns_sec = domain_dns.rpp_to_model(domain["name"], parse_rpp(RPPDnsData, domain["dns"]))
    return (ns.host_attrs if ns else []), dns_sec


def _addresses(host: HostAttr) -> frozenset[str]:
    return frozenset((host.ipv4 or []) + (host.ipv6 or []))


def _client_statuses(domain: dict) -> dict[str, str | None]:
    return {
        status["label"]: status.get("reason")
        for status in domain.get("status") or []
        if status["label"].startswith(CLIENT_STATUS_PREFIX)
    }


def _check_new_statuses(current: dict, patched: dict):
    known = {status["label"] for status in current.get("status") or []}
    for status in patched.get("status") or []:
        if status["label"] not in known and not status["label"].startswith(CLIENT_STATUS_PREFIX):
            raise ValueError(f"Status '{status['label']}' can only be set by the server")


def _dns_sec_items(dns_sec: DnsSec | None) -> list:
    if dns_sec is None:
        return []
    return [*(dns_sec.ds_data or []), *(dns_sec.key_data or [])]


def _dns_sec_difference(wanted: DnsSec | None, current: DnsSec | None) -> DnsSec | None:
    """The data of `wanted` that is not in `current`."""
    current_items = _dns_sec_items(current)
    ds_data = _missing_from(wanted.ds_data or [], current_items, repr) if wanted else []
    key_data = _missing_from(wanted.key_data or [], current_items, repr) if wanted else []
    return DnsSec(ds_data=ds_data or None, key_data=key_data or None) if ds_data or key_data else None


def difference(domain_name: str, current: dict, patched: dict) -> DomainUpdate:
    """The update that turns the current domain (in RPP form) into the patched one."""
    _reject_other_changes(current, patched)
    _check_new_statuses(current, patched)
    current_hosts, patched_hosts = _host_names(current), _host_names(patched)
    current_attrs, patched_attrs = _delegation(current)[0], _delegation(patched)[0]
    current_sec, patched_sec = _delegation(current)[1], _delegation(patched)[1]
    if patched_hosts and patched_attrs:
        raise ValueError("'nameservers' and nameserver records in 'dns' cannot be used together")
    changed_attrs = [
        host for host in patched_attrs
        if any(old.id.lower() == host.id.lower() and _addresses(old) != _addresses(host) for old in current_attrs)
    ]
    add_attrs = _missing_from(patched_attrs, current_attrs, lambda host: host.id.lower()) + changed_attrs
    remove_attrs = _missing_from(current_attrs, patched_attrs, lambda host: host.id.lower()) + [
        old for old in current_attrs if any(old.id.lower() == host.id.lower() for host in changed_attrs)
    ]
    add_hosts = _missing_from(patched_hosts, current_hosts, str.lower)
    remove_hosts = _missing_from(current_hosts, patched_hosts, str.lower)

    add_sec, remove_sec = _dns_sec_difference(patched_sec, current_sec), _dns_sec_difference(current_sec, patched_sec)
    if add_sec and add_sec.ds_data and add_sec.key_data:
        raise NotSupportedByProxy("'ds' and 'dnskey' records in one request")

    current_pairs, patched_pairs = _contact_pairs(current), _contact_pairs(patched)
    add_contacts = _references(_missing_from(patched_pairs, current_pairs, _pair_key)) or []
    remove_contacts = _references(_missing_from(current_pairs, patched_pairs, _pair_key)) or []
    registrant_before, registrant_after = _registrant(current), _registrant(patched)
    if registrant_after is not None and (registrant_before is None or registrant_after.lower() != registrant_before.lower()):
        add_contacts.append(ContactReferenceNew(type=REGISTRANT, contact=ContactMinimal(id=registrant_after)))
    elif registrant_after is None and registrant_before is not None:
        remove_contacts.append(ContactReferenceNew(type=REGISTRANT, contact=ContactMinimal(id="")))

    status_before, status_after = _client_statuses(current), _client_statuses(patched)
    new_reason = {label for label in status_before.keys() & status_after.keys() if status_after[label] not in (None, status_before[label])}
    add_status = sorted(status_after.keys() - status_before.keys() | new_reason)
    remove_status = sorted(status_before.keys() - status_after.keys() | new_reason)

    def hosts(object_names: list[str], attrs: list[HostAttr]) -> NS | None:
        if object_names:
            return NS(host_objs=[HostObj(id=name) for name in object_names], host_attrs=None)
        return NS(host_objs=None, host_attrs=attrs) if attrs else None

    add = DomainUpdateAdd(
        ns=hosts(add_hosts, add_attrs), contacts=add_contacts or None, dnsSEC=add_sec,
        status=add_status or None,
        status_reasons={label: status_after[label] for label in add_status if status_after[label]} or None,
    )
    remove = DomainUpdateRemove(
        ns=hosts(remove_hosts, remove_attrs), contacts=remove_contacts or None, dnsSEC=remove_sec,
        status=remove_status or None,
    )
    return DomainUpdate(
        name=domain_name,
        add=add if add.ns or add.contacts or add.dnsSEC or add.status else None,
        remove=remove if remove.ns or remove.contacts or remove.dnsSEC or remove.status else None,
    )
