from core.model.contact.contact_replacement import ContactReplacement
from core.model.contact.contacts import Contact
from core.model.shared.common import AuthInfo
from rpp.dto.rpp_contact import RPPContact
from rpp.mapping.contact import contacts
from rpp.mapping.shared import auth_info, include_elements
from rpp.mapping.shared.common import parse_rpp, reject_set
from rpp.schema.validator import validate_schema

TYPE = "@type"

CHANGEABLE = ("contactInfo", "status", "authInfo", "disclose")

OBJECT = "contact"


def replacement_from_rpp(
    contact_rpp: RPPContact, password: AuthInfo | None, unchanged: frozenset[str],
) -> ContactReplacement:
    """The contact a full update or a patched read asks for. A `due` date has no place in EPP. The caller converts
    `authInfo`, which a read need not show, and names the members the request leaves `unchanged`."""
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
        authInfo=password,
        unchanged=unchanged,
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
    unchanged = include_elements.left_alone(OBJECT, rpp, requested)
    return replacement_from_rpp(contact_rpp, auth_info.rpp_to_model(contact_rpp.authInfo), unchanged)
