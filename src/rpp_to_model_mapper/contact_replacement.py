from dataclasses import replace

from models import Contact, ContactUpdate, LocalizedPostalInfo
from rpp_schema_validator import validate_schema
from . import auth_info, contact_difference, contacts
from .common import parse_rpp, reject_set
from .rpp_models import RPPContact

TYPE = "@type"
CHANGEABLE = ("contactInfo", "status", "authInfo", "disclose")


def wanted_statuses(contact: Contact, contact_rpp: RPPContact) -> Contact:
    """The contact with the statuses the request names. A `due` date has no place in EPP."""
    for status in contact_rpp.status or []:
        reject_set(due=status.due)
    contact.status = [status.label for status in contact_rpp.status or []]
    contact.status_reasons = {status.label: status.reason for status in contact_rpp.status or [] if status.reason}
    return contact


def _kept_localization(wanted: Contact, current: Contact) -> LocalizedPostalInfo | None:
    """The localization of a replacement that has none: the current one stays, with the organisation it shared
    with the card, because EPP can clear that."""
    kept = current.localizedPostalInfo
    if contact_difference.loc_matches_card(current):
        return None
    if kept and kept.organisationName == current.organisationName:
        return replace(kept, organisationName=wanted.organisationName)
    return kept


def _complete_localization(localization: LocalizedPostalInfo, merged: Contact, before: LocalizedPostalInfo | None) -> LocalizedPostalInfo:
    """EPP needs a complete form, so what the localization leaves out comes from the card, then from the stored form."""
    return replace(
        localization,
        name=localization.name or merged.name or (before.name if before else None),
        address=localization.address or merged.address or (before.address if before else None),
    )


def _keeping_what_epp_cannot_clear(wanted: Contact, current: Contact) -> Contact:
    """core §16.8 clears what a full update omits, subject to server policy. EPP cannot clear these, so they stay."""
    merged = replace(
        wanted,
        name=wanted.name or current.name,
        address=wanted.address or current.address,
        email=wanted.email or current.email,
    )
    localization = wanted.localizedPostalInfo
    merged.localizedPostalInfo = (
        _complete_localization(localization, merged, current.localizedPostalInfo)
        if localization else _kept_localization(wanted, current)
    )
    return contact_difference.with_stored_localization(merged, current)


def _wanted(contact_rpp: RPPContact) -> Contact:
    wanted = wanted_statuses(contacts.contact_from_rpp(contact_rpp), contact_rpp)
    wanted.authInfo = auth_info.rpp_to_model(contact_rpp.authInfo)
    return wanted


def rpp_to_model(contact_id: str, rpp: dict) -> dict:
    """Checks a full update and returns it.

    A member outside `contact.update` is rejected, also a create-only or a read-only one (json §4.4, core §16.8).
    """
    validate_schema("contact.update", rpp)
    for member in rpp.keys() - {TYPE, *CHANGEABLE}:
        raise ValueError(f"'{member}' cannot be sent in a full update")
    _wanted(parse_rpp(RPPContact, {**rpp, "id": contact_id}))  # rejects undeclared members at any depth
    return rpp


def rpp_to_model_with_current(contact_id: str, rpp: dict, current: Contact) -> ContactUpdate:
    """The update that turns the current contact into the replacement.

    What the replacement omits is cleared (the organisation and the numbers), except what EPP cannot clear and the `authInfo`.
    """
    wanted = _wanted(parse_rpp(RPPContact, {**rpp, "id": contact_id}))
    return contact_difference.difference(contact_id, current, _keeping_what_epp_cannot_clear(wanted, current))
