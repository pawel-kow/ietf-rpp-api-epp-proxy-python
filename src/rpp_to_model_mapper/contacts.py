from models import *
from .rpp_models import *
from rpp_schema_validator import validate_schema
from .common import provisioning_object_to_rpp

def rpp_to_contact(rpp: dict) -> Contact:
    """Converts a JSON string to a Contact object according to the provided schema."""
    # First validate the schema
    validate_schema("Contact", rpp)
    contact_rpp = RPPContact.from_dict(rpp)
    # Create a Domain object from the request body
    contact = Contact(
        id = contact_rpp.id if contact_rpp.id else None,
        name = contact_rpp.name if contact_rpp.name else None,
        organisationName = contact_rpp.organisationName if contact_rpp.organisationName else None,
        type = ContactType(contact_rpp.contactType.value),
        email = contact_rpp.email if contact_rpp.email else None,
        phone = contact_rpp.phone if contact_rpp.phone else None,
        fax = contact_rpp.fax if contact_rpp.fax else None,
        address = Address(
            street = contact_rpp.address.street,
            city = contact_rpp.address.city,
            stateProvince = contact_rpp.address.stateProvince,
            postalCode = contact_rpp.address.postalCode,
            country = contact_rpp.address.country
        ) if contact_rpp.address is not None else None,
        authInfo= AuthInfo(
            pw=contact_rpp.authInfo.pw if contact_rpp.authInfo and contact_rpp.authInfo.pw else None,
            hash=contact_rpp.authInfo.hash if contact_rpp.authInfo and contact_rpp.authInfo.hash else None
        ) if contact_rpp.authInfo else None
    )
    return contact

def contact_to_rpp(contact: Contact) -> str:
    """Converts a Contact object to a JSON string according to the provided schema."""

    contact_dict = {}
    contact_dict["id"] = contact.id
    if contact.name is not None:
        contact_dict["name"] = contact.name
    if contact.organisationName is not None:
        contact_dict["organisationName"] = contact.organisationName
    contact_dict["contactType"] = contact.type.value
    if contact.email is not None:
        contact_dict["email"] = contact.email
    if contact.phone is not None:
        contact_dict["phone"] = contact.phone
    if contact.fax is not None:
        contact_dict["fax"] = contact.fax
    if contact.address is not None:
        contact_dict["address"] = {}
        if contact.address.street is not None:
            contact_dict["address"]["street"] = contact.address.street
        if contact.address.city is not None:
            contact_dict["address"]["city"] = contact.address.city
        if contact.address.stateProvince is not None:
            contact_dict["address"]["stateProvince"] = contact.address.stateProvince
        if contact.address.postalCode is not None:
            contact_dict["address"]["postalCode"] = contact.address.postalCode
        if contact.address.country is not None:
            contact_dict["address"]["country"] = contact.address.country

    provisioning_object_to_rpp(contact, contact_dict)

    validate_schema("Contact", contact_dict)
    return contact_dict
