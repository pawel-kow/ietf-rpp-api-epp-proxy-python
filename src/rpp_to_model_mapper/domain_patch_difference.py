from models import (
    ContactMinimal, ContactReferenceNew, DnsSec, DomainUpdate, DomainUpdateAdd, DomainUpdateRemove, HostAttr, HostObj, NS,
)
from . import domain_dns
from .common import parse_rpp, reject_set
from .domains import REGISTRANT, check_contact_label
from .not_supported_by_proxy import NotSupportedByProxy
from .patch_statuses import is_client_label
from .rpp_models import RPPDnsData

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


NAMESERVER_RECORDS = ("ns", "a", "aaaa")


def _delegation(domain: dict, checked: bool = True) -> tuple[list[HostAttr], DnsSec | None]:
    """The host attributes and DNSSEC data of the records of `dns`. The current domain is not `checked`."""
    if not domain.get("dns"):
        return [], None
    ns, dns_sec = domain_dns.rpp_to_model(domain["name"], parse_rpp(RPPDnsData, domain["dns"]), checked)
    return (ns.host_attrs if ns else []), dns_sec


def _addresses(host: HostAttr) -> frozenset[str]:
    return frozenset((host.ipv4 or []) + (host.ipv6 or []))


def _client_statuses(domain: dict) -> dict[str, str | None]:
    for status in domain.get("status") or []:
        reject_set(due=status.get("due"))
    reasons: dict[str, str | None] = {}
    for status in domain.get("status") or []:
        label, reason = status["label"], status.get("reason") or None
        if is_client_label(label) and (reason or label not in reasons):
            reasons[label] = reason
    return reasons


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


def _reject_nameservers_with_records(domain: dict):
    """`nameservers` cannot go with the records that delegate (data-objects §11.2). `ds` and `dnskey` can, see spec-issues.md."""
    records = (domain.get("dns") or {}).get("records") or []
    if domain.get("nameservers") and any(str(record.get("type")).lower() in NAMESERVER_RECORDS for record in records):
        raise ValueError("'nameservers' and nameserver records in 'dns' cannot be used together")


def _nameserver_changes(
    current_objs: list[str], current_attrs: list[HostAttr], wanted_objs: list[str], wanted_attrs: list[HostAttr],
) -> tuple[list[str], list[str], list[HostAttr], list[HostAttr]]:
    """What EPP adds and removes to turn the current delegation into the wanted one.

    A host is the same in both forms, whatever the case. The addresses of a host object live on the host, so a
    host attribute with addresses is never the same as a host object: it is removed and added. Current host
    attributes against other wanted host objects are all removed and all added.
    """
    def by_name(attrs):
        return {host.id.lower(): host for host in attrs}

    current_by_name, wanted_by_name = by_name(current_attrs), by_name(wanted_attrs)
    current_obj_names = {name.lower() for name in current_objs}
    wanted_obj_names = {name.lower() for name in wanted_objs}

    changed_attrs = [
        host for name, host in wanted_by_name.items()
        if name in current_by_name and _addresses(current_by_name[name]) != _addresses(host)
    ]
    add_attrs = [
        host for name, host in wanted_by_name.items()
        if (name not in current_by_name and (name not in current_obj_names or _addresses(host)))
    ] + changed_attrs
    remove_attrs = [
        host for name, host in current_by_name.items()
        if (name not in wanted_by_name and (name not in wanted_obj_names or _addresses(host)))
    ] + [current_by_name[host.id.lower()] for host in changed_attrs]
    if current_by_name and wanted_objs and not current_objs and (
        current_by_name.keys() != wanted_obj_names or any(_addresses(host) for host in current_by_name.values())
    ):
        # EPP takes host objects or host attributes, not both: a registry that shows attributes stores them.
        return _missing_from(wanted_objs, [], str.lower), [], [], list(current_by_name.values())
    add_hosts = _missing_from(wanted_objs, current_objs, str.lower)
    add_hosts = [name for name in add_hosts if name.lower() not in current_by_name or _addresses(current_by_name[name.lower()])]
    remove_hosts = _missing_from(current_objs, wanted_objs, str.lower)
    remove_hosts = [name for name in remove_hosts if name.lower() not in wanted_by_name or _addresses(wanted_by_name[name.lower()])]
    return add_hosts, remove_hosts, add_attrs, remove_attrs


def difference(domain_name: str, current: dict, patched: dict) -> DomainUpdate:
    """The update that turns the current domain (in RPP form) into the patched one."""
    _reject_other_changes(current, patched)
    _reject_nameservers_with_records(patched)
    current_attrs, current_sec = _delegation(current, checked=False)
    patched_attrs, patched_sec = _delegation(patched, checked=patched.get("dns") != current.get("dns"))
    add_hosts, remove_hosts, add_attrs, remove_attrs = _nameserver_changes(
        _host_names(current), current_attrs, _host_names(patched), patched_attrs,
    )

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
    new_reason = {label for label in status_before.keys() & status_after.keys() if status_after[label] != status_before[label]}
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
