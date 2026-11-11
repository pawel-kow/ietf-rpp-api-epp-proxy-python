from dataclasses import replace

from .contact_replacement import ContactReplacement
from .contacts import Contact
from .localized_postal_info import LocalizedPostalInfo


def _card(contact: Contact | ContactReplacement) -> tuple:
    return contact.name, contact.organisationName, contact.address


def loc_matches_card(current: Contact) -> bool:
    """A localization equal to the card reads back as none (`contacts._localizations_to_rpp`)."""
    return current.localizedPostalInfo == LocalizedPostalInfo(
        name=current.name, organisationName=current.organisationName, address=current.address,
    )


def _read_localization(current: Contact) -> LocalizedPostalInfo | None:
    """The localization a request that repeats the read of the contact asks for. A read shows only the members that
    differ from the card, and the request inherits the rest from it."""
    loc = current.localizedPostalInfo
    if loc is None:
        return None
    shown = [value for value, card in zip((loc.name, loc.organisationName, loc.address), _card(current)) if value and value != card]
    if not shown:
        return None
    return LocalizedPostalInfo(
        name=loc.name or current.name,
        organisationName=loc.organisationName or current.organisationName,
        address=loc.address or current.address,
    )


def _with_stored_localization(wanted: ContactReplacement, current: Contact) -> ContactReplacement:
    """A wanted localization that is what a read of the current one gives is the current one, unless the request
    changes the card members the stored form lacks, which the localization inherits."""
    loc = current.localizedPostalInfo
    stored = (loc.name, loc.organisationName, loc.address) if loc else (None, None, None)
    unchanged_card = wanted.localizedPostalInfo is None or all(
        wanted_member == current_member
        for has, wanted_member, current_member in zip(stored, _card(wanted), _card(current)) if not has
    )
    if unchanged_card and wanted.localizedPostalInfo == _read_localization(current) and not loc_matches_card(current):
        return replace(wanted, localizedPostalInfo=current.localizedPostalInfo)
    return wanted


def as_stored(wanted: ContactReplacement, current: Contact) -> ContactReplacement:
    """The wanted contact in the terms of the stored one, as an RPP read represents a localization by its differences
    from the card. A localization equal to the card reads as none, so a request without one keeps it equal to the
    wanted card. A localization the request repeats from the read is the stored one, so that the members the stored
    form lacks are not filled in from the card."""
    if wanted.localizedPostalInfo is None and current.localizedPostalInfo is not None and loc_matches_card(current):
        return replace(wanted, localizedPostalInfo=LocalizedPostalInfo(
            name=wanted.name, organisationName=wanted.organisationName, address=wanted.address,
        ))
    return _with_stored_localization(wanted, current)
