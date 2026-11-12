from dataclasses import replace

from core.capabilities.backend_profile import BackendProfile

# What DENIC RRI 5.0 holds (docs/rri/refactoring.md §3.7, gap-analysis §7).
RRI_PROFILE = BackendProfile(
    name="RRI",
    contact_labels=("generalRequest", "abuse"),  # REQUEST contacts (gap Q2); there are no admin, tech or billing
    max_registrants=5,  # holders 1 to 5 (gap Q1)
    domain_record_types=("ns", "a", "aaaa", "mx", "dnskey"),  # Nserver, Nsentry and Dnskey; DENIC computes the DS
    host_objects=False,
    client_statuses=False,  # every status is the registry's
    contact_fax=False,
    contact_localization=False,
    contact_region=False,
    contact_phones_max=1,
    contact_kind_held=True,  # PERSON or ORG, a PERSON may name its organisation
    contact_org_person_name=False,  # an ORG is named by its organisation
    contact_name_changeable=False,  # the name is immutable (63220080801)
    contact_auth_info=False,  # an RRI contact has no AuthInfo
    supports_renew=False,  # domains run until deleted
    supports_contact_delete=False,  # the registry deletes contacts itself
    domain_transfer_operations=frozenset(),  # CHPROV is not exposed (gap Q3, option C)
    contact_transfer_operations=frozenset(),
    restore_report=False,  # RESTORE is one step (gap Q6)
    auth_info_readable=False,  # RRI holds the hash of an AuthInfo1 only
    domain_dns_required=True,  # 1 to 20 dnsentry
    contact_phone_required=True,  # mandatory since 2026-01-28
    registrant_required=True,  # 1 to 5 holders
    registration_periods=False,  # a domain runs until it is deleted
    metadata=frozenset({"domainName.crDate", "domainName.upDate", "contact.upDate"}),  # registrationDate, changed
    objects=("domainName", "contact"),
    profiles=(),  # the EPP compatibility profile does not describe RRI (refactoring.md §3.10)
)


def rri_profile(lgr: str | None) -> BackendProfile:
    """The profile of an RRI backend, which offers the one LGR configured for DENIC's repertoire, if any (gap Q11)."""
    return replace(RRI_PROFILE, lgrs=frozenset({lgr}) if lgr else frozenset())
