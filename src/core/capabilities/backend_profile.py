from dataclasses import dataclass


@dataclass(frozen=True, kw_only=True)
class BackendProfile:
    """What a registry backend can hold, which the RPP mappers and discovery check. Static per backend.

    `name` names the backend in a refusal (`… cannot be expressed in <name>`).
    `contact_labels` are the contact roles of a domain besides the registrant, and `max_registrants` how many
    registrants a domain has at most.
    `domain_record_types` are the DNS record types a domain holds at its apex. Address records of its nameservers
    are glue, which every backend holds.
    `host_objects` is whether hosts are objects of their own, `client_statuses` whether a client can set statuses.
    `contact_fax`, `contact_localization` and `contact_region` are whether a contact holds a fax number, a localized
    form and a region in its address, and `contact_phones_max` how many voice numbers it holds.
    `supports_renew`, `supports_contact_delete` and `supports_transfer_query` are whether the backend has these
    commands.
    `objects` are the data objects and `profiles` the profiles the discovery document states.
    `lgrs` are the label generation rulesets the backend offers for IDNs, none when it takes no IDN.
    """
    name: str
    contact_labels: tuple[str, ...]
    max_registrants: int
    domain_record_types: tuple[str, ...]
    host_objects: bool
    client_statuses: bool
    contact_fax: bool
    contact_localization: bool
    contact_region: bool
    contact_phones_max: int
    supports_renew: bool
    supports_contact_delete: bool
    supports_transfer_query: bool
    objects: tuple[str, ...]
    profiles: tuple[str, ...]
    lgrs: frozenset[str] = frozenset()
