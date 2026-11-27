from core.model.shared.availability import Availability
from extensions.rri.rpp.dto.rpp_request_contact_availability import RPPRequestContactAvailability
from rpp.schema.validator import validate_schema


def model_to_rpp(check: Availability, extensions: tuple[str, ...] = ()) -> dict:
    """A request contact shares its handles with the contacts of the registry, so a handle a contact has is not
    available."""
    availability = RPPRequestContactAvailability(
        available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("requestContactAvailability.read", availability, extensions)
    return availability
