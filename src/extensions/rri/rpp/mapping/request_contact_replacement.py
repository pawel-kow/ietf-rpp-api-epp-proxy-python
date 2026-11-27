from extensions.rri.core.model.request_contact import RequestContact
from extensions.rri.rpp.dto.rpp_request_contact_update import RPPRequestContactUpdate
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_request_schema

TYPE = "@type"

CHANGEABLE = ("uriTemplate",)


def rpp_to_model(contact_id: str, rpp: dict, extensions: tuple[str, ...] = ()) -> RequestContact:
    """Converts a full update to the request contact it asks for. A member outside `requestContact.update` is
    rejected, also a create-only or a read-only one (json §4.4, core §16.8)."""
    validate_request_schema("requestContact.update", rpp, extensions)
    for member in sorted(rpp.keys() - {TYPE, *CHANGEABLE}):
        raise ValueError(f"'{member}' cannot be sent in a full update")
    update = parse_rpp(RPPRequestContactUpdate, rpp)
    return RequestContact(id=contact_id, uriTemplate=update.uriTemplate)
