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
    `supports_renew` and `supports_contact_delete` are whether the backend has these commands.
    `domain_transfer_operations` and `contact_transfer_operations` are the transfer operations (`request`, `query`,
    `cancel`, `approve`, `reject`) the backend has for each object, which the transfer handlers check before any
    command.
    `restore_report` is whether a restore takes a report, which the restore report mappers check.
    `auth_info_readable` is whether a read can show a domain's authInfo, which the domain handlers check against
    `includeElements`.
    `domain_dns_required` is whether a domain needs DNS data (name servers or records) from its create on, and
    `contact_phone_required` whether a contact needs a voice number. The proxy leaves both to the registry to refuse
    (gap Q13); the test selectors read them.
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
    contact_auth_info: bool
    supports_renew: bool
    supports_contact_delete: bool
    domain_transfer_operations: frozenset[str]
    contact_transfer_operations: frozenset[str]
    restore_report: bool
    auth_info_readable: bool
    domain_dns_required: bool
    contact_phone_required: bool
    objects: tuple[str, ...]
    profiles: tuple[str, ...]
    lgrs: frozenset[str] = frozenset()
