from models import AuthInfoIntent, Contact, ContactReplacement
from rpp_schema_validator import validate_schema
from . import auth_info, contacts
from .common import parse_rpp, reject_set
from .rpp_models import RPPContact

TYPE = "@type"
CHANGEABLE = ("contactInfo", "status", "authInfo", "disclose")
OBJECT = "contact"


def replacement_from_rpp(contact_rpp: RPPContact, auth_info_intent: AuthInfoIntent) -> ContactReplacement:
    """The contact a full update or a patched read asks for. A `due` date has no place in EPP."""
    contact: Contact = contacts.contact_from_rpp(contact_rpp)
    for status in contact_rpp.status or []:
        reject_set(due=status.due)
    return ContactReplacement(
        id=contact_rpp.id,
        name=contact.name,
        organisationName=contact.organisationName,
        email=contact.email,
        phone=contact.phone,
        fax=contact.fax,
        address=contact.address,
        localizedPostalInfo=contact.localizedPostalInfo,
        status=[status.label for status in contact_rpp.status or []],
        status_reasons={status.label: status.reason for status in contact_rpp.status or [] if status.reason},
        auth_info=auth_info_intent,
    )


def rpp_to_model(contact_id: str, rpp: dict, requested: frozenset[str] = frozenset()) -> ContactReplacement:
    """Converts a full update to the contact it asks for. What it omits is cleared, except the data elements with
    onDemand Visibility that `requested` (the `includeElements` of the request) does not name.

    A member outside `contact.update` is rejected, also a create-only or a read-only one (json §4.4, core §16.8).
    """
    validate_schema("contact.update", rpp)
    for member in rpp.keys() - {TYPE, *CHANGEABLE}:
        raise ValueError(f"'{member}' cannot be sent in a full update")
    contact_rpp = parse_rpp(RPPContact, {**rpp, "id": contact_id})  # rejects undeclared members at any depth
    return replacement_from_rpp(contact_rpp, auth_info.full_update_intent(OBJECT, rpp, requested))
