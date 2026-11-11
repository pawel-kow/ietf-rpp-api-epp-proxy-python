from dataclasses import replace

from core.capabilities.backend_profile import BackendProfile
from registry_adapter.epp.idn_tables import IdnTables

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
    supports_renew=True,
    supports_contact_delete=True,
    supports_transfer_query=True,
    objects=("domainName", "host", "contact"),
    profiles=("urn:ietf:params:rpp:profile:epp-compatibility",),  # core §12.4, data-objects §2.8, json §8.7.1
)


def epp_profile(idn_tables: IdnTables) -> BackendProfile:
    """The profile of an EPP backend, which offers the LGRs that its IDN tables are mapped from."""
    return replace(EPP_PROFILE, lgrs=idn_tables.lgrs())
