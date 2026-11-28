"""The request contact of the rri extension (docs/rri/rri-extension.md): a handle and a URI template."""
from extensions.rri.core.model.request_contact import RequestContact
from extensions.rri.rpp.dto.rpp_request_contact import RPPRequestContact
from rpp.mapping.shared import prov_metadata
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_request_schema, validate_schema


def check_requested(identifiers: list[str]) -> frozenset[str]:
    """A request contact has no data element with onDemand Visibility, so `includeElements` names none of it."""
    for identifier in identifiers:
        raise ValueError(f"'{identifier}' is not a data element with onDemand Visibility of the requestContact object")
    return frozenset()


def rpp_to_model(rpp: dict, extensions: tuple[str, ...] = ()) -> RequestContact:
    """Converts a create request. The registry checks the template beyond its length."""
    validate_request_schema("requestContact.create", rpp, extensions)
    contact = parse_rpp(RPPRequestContact, rpp)
    return RequestContact(id=contact.id, uriTemplate=contact.uriTemplate)


def model_to_rpp(contact: RequestContact, extensions: tuple[str, ...] = ()) -> dict:
    """Converts a request contact to its read representation."""
    contact_dict = RPPRequestContact(
        id=contact.id,
        provMetadata=prov_metadata.model_to_rpp(contact),
        uriTemplate=contact.uriTemplate,
    ).to_rpp()
    validate_schema("requestContact.read", contact_dict, extensions)
    return contact_dict
