from core.model.contact import contact_difference, contact_localization
from core.model.contact.address import Address
from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contact_update import ContactUpdate
from core.model.contact.contacts import Contact, ContactType
from core.model.contact.localized_postal_info import LocalizedPostalInfo
from core.model.shared.common import AuthInfo
from registry_adapter.epp import contact_refusal
from rpp.http.problem import raise_registry_error

ADDRESS = Address(street=["1 Main"], city="Berlin", stateProvince="BE", postalCode="10115", country="DE")


def current_contact(**members) -> Contact:
    """A contact as the registry reads it: a person with an address, an email and both numbers."""
    fields = dict(
        id="JD-1234", roid="C1", type=ContactType.PERSON, name="John Doe", email=["a@example.example"],
        phone=["+49.123x12"], fax=["+49.456"], address=ADDRESS, status=["ok"], clID="foo", crID="foo",
        crDate="2026-11-04T10:00:00.000000Z", authInfo=AuthInfo(pw="Secret1!x"),
    )
    return Contact(**{**fields, **members})


def card(**extra) -> dict:
    """The Card of `current_contact()`, as a request holds it."""
    return {
        "@type": "Card", "version": "2.0", "kind": "individual", "name": {"full": "John Doe"},
        "addresses": {"addr": {"components": [
            {"kind": "name", "value": "1 Main"}, {"kind": "locality", "value": "Berlin"},
            {"kind": "region", "value": "BE"}, {"kind": "postcode", "value": "10115"},
        ], "countryCode": "DE"}},
        "phones": {"voice": {"number": "tel:+49.123;ext=12"}, "fax": {"number": "tel:+49.456", "features": {"fax": True}}},
        "emails": {"email": {"address": "a@example.example"}},
        **extra,
    }


def put_body(contact_info=None, **extra) -> dict:
    return {"@type": "contact", "contactInfo": contact_info or card(), **extra}


def localized(**members) -> LocalizedPostalInfo:
    return LocalizedPostalInfo(**members)


def derived_update(current: Contact, wanted: ContactReplacement) -> ContactUpdate:
    """The EPP update the EPP adapter derives from a full update, without the registry; a refusal as the handler renders it."""
    wanted = contact_localization.as_stored(wanted, current)
    refused = contact_refusal.refuse(current, wanted)
    if refused:
        raise_registry_error(refused)
    return contact_difference.difference(current, wanted)
