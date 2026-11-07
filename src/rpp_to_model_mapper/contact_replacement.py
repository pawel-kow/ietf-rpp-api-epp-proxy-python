from dataclasses import replace

from models import Contact, ContactUpdate
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


def _keeping_what_epp_cannot_clear(wanted: Contact, current: Contact) -> Contact:
    """core §16.8 clears what a full update omits, subject to server policy. EPP cannot clear these, so they stay."""
    return replace(
        wanted,
        name=wanted.name or current.name,
        address=wanted.address or current.address,
        email=wanted.email or current.email,
        localizedPostalInfo=wanted.localizedPostalInfo or (
            None if contact_difference.loc_matches_card(current) else current.localizedPostalInfo
        ),
    )


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
