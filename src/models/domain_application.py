from .auth_info_intent import AuthInfoIntent
from .client_statuses import client_statuses
from .dns_sec import DnsSec
from .domain_difference import (
    REGISTRANT, contacts_of, dns_sec_of, host_attributes_of, host_objects_of, registrant_of,
)
from .domain_replacement import DomainReplacement
from .domains import Domain, DomainUpdate, DomainUpdateChange, HostObj, NS


def _without(values: list, removed: list, key) -> list:
    gone = {key(value) for value in removed}
    return [value for value in values if key(value) not in gone]


def _with(values: list, added: list, key) -> list:
    known = {key(value) for value in values}
    return values + [value for value in added if key(value) not in known]


def _ns(current: NS | None, delta: DomainUpdate) -> NS | None:
    added = delta.add.ns if delta.add else None
    removed = delta.remove.ns if delta.remove else None
    objs = _without(host_objects_of(current), host_objects_of(removed), str.lower)
    objs = _with(objs, host_objects_of(added), str.lower)
    attrs = _without(host_attributes_of(current), host_attributes_of(removed), lambda host: host.id.lower())
    attrs = _with(attrs, host_attributes_of(added), lambda host: host.id.lower())
    if objs:
        return NS(host_objs=[HostObj(id=name) for name in objs], host_attrs=None)
    return NS(host_objs=None, host_attrs=attrs) if attrs else None


def _dns_sec(current: DnsSec | None, delta: DomainUpdate) -> DnsSec | None:
    added = dns_sec_of(delta.add.dnsSEC if delta.add else None)
    removed = dns_sec_of(delta.remove.dnsSEC if delta.remove else None)
    items = {}
    for kind in ("ds_data", "key_data"):
        values = _without(getattr(current, kind) or [] if current else [], getattr(removed, kind) or [] if removed else [], repr)
        items[kind] = _with(values, getattr(added, kind) or [] if added else [], repr) or None
    return DnsSec(**items) if items["ds_data"] or items["key_data"] else None


def _auth_info(change: DomainUpdateChange | None) -> AuthInfoIntent:
    if change and change.clear_auth_info:
        return AuthInfoIntent.clear()
    if change and change.authInfo:
        return AuthInfoIntent.set(change.authInfo)
    return AuthInfoIntent.keep()


def apply(current: Domain, delta: DomainUpdate) -> DomainReplacement:
    """The domain the update asks for: the current domain with the changes of the update. A registrant in the added
    contacts replaces the current one, one in the removed contacts clears it."""
    added_contacts = (delta.add.contacts if delta.add else None) or []
    removed_contacts = (delta.remove.contacts if delta.remove else None) or []

    def key(contact):
        return contact.type, contact.contact.id.lower()

    contacts = _without(contacts_of(current), [c for c in removed_contacts if c.type != REGISTRANT], key)
    contacts = _with(contacts, [c for c in added_contacts if c.type != REGISTRANT], key)
    registrant = registrant_of(current)
    if any(c.type == REGISTRANT for c in removed_contacts):
        registrant = None
    for contact in added_contacts:
        if contact.type == REGISTRANT:
            registrant = contact.contact.id
    statuses = client_statuses(current.status, current.status_reasons)
    for label in (delta.remove.status if delta.remove else None) or []:
        statuses.pop(label, None)
    for label in (delta.add.status if delta.add else None) or []:
        statuses[label] = ((delta.add.status_reasons or {}).get(label)) or None
    return DomainReplacement(
        name=delta.name,
        ns=_ns(current.ns, delta),
        registrant=registrant,
        contacts=contacts,
        dnsSEC=_dns_sec(dns_sec_of(current.dnsSEC), delta),
        status=list(statuses),
        status_reasons={label: reason for label, reason in statuses.items() if reason},
        auth_info=_auth_info(delta.change),
    )
