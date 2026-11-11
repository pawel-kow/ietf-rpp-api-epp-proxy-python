from dataclasses import replace

from core.model.contact.contacts import ContactMinimal
from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_replacement import DomainReplacement
from core.model.domain.domains import (
    ContactReferenceNew, Domain, DomainUpdate, DomainUpdateAdd, DomainUpdateChange, DomainUpdateRemove, HostAttr,
    HostObj, NS,
)
from core.model.shared.client_statuses import client_statuses, status_changes
from core.model.shared.common import password_of
from core.model.shared.stated_members import stated

REGISTRANT = "registrant"


def _missing_from(values: list, others: list, key=lambda value: value) -> list:
    """The values whose key is not among the others, in their order and without repeats."""
    known = {key(other) for other in others}
    missing = []
    for value in values:
        if key(value) not in known:
            known.add(key(value))
            missing.append(value)
    return missing


def registrant_of(domain: Domain) -> str | None:
    for contact in domain.contacts or []:
        if REGISTRANT in contact.types:
            return contact.id
    return None


def contacts_of(domain: Domain) -> list[ContactReferenceNew]:
    """The contacts of the domain other than the registrant, one per role."""
    return [
        ContactReferenceNew(type=label, contact=ContactMinimal(id=contact.id))
        for contact in domain.contacts or [] for label in contact.types if label != REGISTRANT
    ]


def host_objects_of(ns: NS | None) -> list[str]:
    return [host.id for host in (ns.host_objs if ns else None) or []]


def host_attributes_of(ns: NS | None) -> list[HostAttr]:
    return list((ns.host_attrs if ns else None) or [])


def dns_sec_of(dns_sec: DnsSec | None) -> DnsSec | None:
    """The DNSSEC data with the digests in uppercase, as a domain's records hold them."""
    if dns_sec is None:
        return None
    return replace(dns_sec, ds_data=[replace(ds, digest=ds.digest.upper()) for ds in dns_sec.ds_data] if dns_sec.ds_data else dns_sec.ds_data)


def _addresses(host: HostAttr) -> frozenset[str]:
    return frozenset((host.ipv4 or []) + (host.ipv6 or []))


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


def _nameserver_changes(
    current_objs: list[str], current_attrs: list[HostAttr], wanted_objs: list[str], wanted_attrs: list[HostAttr],
) -> tuple[list[str], list[str], list[HostAttr], list[HostAttr]]:
    """What is added and removed to turn the current delegation into the wanted one.

    A host is the same in both forms, whatever the case. The addresses of a host object live on the host, so a
    host attribute with addresses is never the same as a host object: it is removed and added. Current host
    attributes against wanted host objects are all removed and all added when the names differ or any of them
    has an address.
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
        # A domain takes host objects or host attributes, not both: a registry that shows attributes stores them.
        return _missing_from(wanted_objs, [], str.lower), [], [], list(current_by_name.values())
    add_hosts = _missing_from(wanted_objs, current_objs, str.lower)
    add_hosts = [name for name in add_hosts if name.lower() not in current_by_name or _addresses(current_by_name[name.lower()])]
    remove_hosts = _missing_from(current_objs, wanted_objs, str.lower)
    remove_hosts = [name for name in remove_hosts if name.lower() not in wanted_by_name or _addresses(wanted_by_name[name.lower()])]
    return add_hosts, remove_hosts, add_attrs, remove_attrs


def _pair_key(contact: ContactReferenceNew) -> tuple[str, str]:
    return contact.type, contact.contact.id.lower()


def _contact_changes(current: Domain, wanted: DomainReplacement) -> tuple[list[ContactReferenceNew], list[ContactReferenceNew]]:
    current_contacts = contacts_of(current)
    add = _missing_from(wanted.contacts, current_contacts, _pair_key)
    remove = _missing_from(current_contacts, wanted.contacts, _pair_key)
    before, after = registrant_of(current), wanted.registrant
    if after is not None and (before is None or after.lower() != before.lower()):
        add.append(ContactReferenceNew(type=REGISTRANT, contact=ContactMinimal(id=after)))
    elif after is None and before is not None:
        remove.append(ContactReferenceNew(type=REGISTRANT, contact=ContactMinimal(id="")))
    return add, remove


def _auth_info_change(current: Domain, wanted: DomainReplacement) -> DomainUpdateChange | None:
    """A password that differs is set, one the replacement omits is cleared. A registry that does not show the
    password makes any wanted one differ, so it is sent."""
    if password_of(wanted) == password_of(current):
        return None
    return DomainUpdateChange(authInfo=wanted.authInfo) if wanted.authInfo else DomainUpdateChange(clear_auth_info=True)


def _hosts(object_names: list[str], attrs: list[HostAttr]) -> NS | None:
    if object_names:
        return NS(host_objs=[HostObj(id=name) for name in object_names], host_attrs=None)
    return NS(host_objs=None, host_attrs=attrs) if attrs else None


def difference(current: Domain, wanted: DomainReplacement) -> DomainUpdate:
    """The update that turns the current domain into the wanted one (core §16.8: what is omitted is cleared)."""
    wanted = stated(wanted, current)
    add_hosts, remove_hosts, add_attrs, remove_attrs = _nameserver_changes(
        host_objects_of(current.ns), host_attributes_of(current.ns),
        host_objects_of(wanted.ns), host_attributes_of(wanted.ns),
    )
    current_sec = dns_sec_of(current.dnsSEC)
    add_sec, remove_sec = _dns_sec_difference(wanted.dnsSEC, current_sec), _dns_sec_difference(current_sec, wanted.dnsSEC)
    add_contacts, remove_contacts = _contact_changes(current, wanted)
    after = client_statuses(wanted.status, wanted.status_reasons)
    add_status, remove_status = status_changes(client_statuses(current.status, current.status_reasons), after)
    add = DomainUpdateAdd(
        ns=_hosts(add_hosts, add_attrs), contacts=add_contacts or None, dnsSEC=add_sec,
        status=add_status or None,
        status_reasons={label: after[label] for label in add_status if after[label]} or None,
    )
    remove = DomainUpdateRemove(
        ns=_hosts(remove_hosts, remove_attrs), contacts=remove_contacts or None, dnsSEC=remove_sec,
        status=remove_status or None,
    )
    return DomainUpdate(
        name=wanted.name,
        add=add if add.ns or add.contacts or add.dnsSEC or add.status else None,
        remove=remove if remove.ns or remove.contacts or remove.dnsSEC or remove.status else None,
        change=_auth_info_change(current, wanted),
    )


def changes_nothing(update: DomainUpdate) -> bool:
    return update.add is None and update.remove is None and update.change is None
