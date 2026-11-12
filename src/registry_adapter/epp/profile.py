from dataclasses import replace

from core.capabilities.backend_profile import BackendProfile
from registry_adapter.epp.idn_tables import IdnTables

# RFC 5730 §2.9.3.4
TRANSFER_OPERATIONS = frozenset({"request", "query", "cancel", "approve", "reject"})

EPP_PROFILE = BackendProfile(
    name="EPP",
    contact_labels=("admin", "billing", "tech"),  # RFC 5731 §2.2
    max_registrants=1,
    domain_record_types=("ns", "ds", "dnskey"),  # host attributes (RFC 5731) and secDNS (RFC 5910)
    host_objects=True,
    client_statuses=True,
    contact_fax=True,
    contact_localization=True,
    contact_region=True,
    contact_phones_max=1,
    contact_org_person_name=True,  # RFC 5733 postalInfo name and org
    contact_name_changeable=True,
    contact_auth_info=True,  # RFC 5733 §2.8
    supports_renew=True,
    supports_contact_delete=True,
    domain_transfer_operations=TRANSFER_OPERATIONS,
    contact_transfer_operations=TRANSFER_OPERATIONS,
    restore_report=True,  # RFC 3915 §4.2.5
    auth_info_readable=True,
    domain_dns_required=False,  # RFC 5731 §3.2.1: ns is optional
    contact_phone_required=False,  # RFC 5733 §3.2.1: voice is optional
    registrant_required=False,  # RFC 5731 §3.2.1: registrant is optional
    registration_periods=True,  # RFC 5731 §2.6
    metadata=frozenset(f"{obj}.{member}" for obj in ("domainName", "contact")
                       for member in ("crClientId", "crDate", "upClientId", "upDate", "trDate")),
    objects=("domainName", "host", "contact"),
    profiles=("urn:ietf:params:rpp:profile:epp-compatibility",),  # core §12.4, data-objects §2.8, json §8.7.1
)


def epp_profile(idn_tables: IdnTables) -> BackendProfile:
    """The profile of an EPP backend, which offers the LGRs that its IDN tables are mapped from."""
    return replace(EPP_PROFILE, lgrs=idn_tables.lgrs())
