from rpp.schema.validator import validate_schema
from rpp.dto.rpp_contact_availability import RPPContactAvailability
from core.model.shared.availability import Availability


def model_to_rpp(check: Availability) -> dict:
    availability = RPPContactAvailability(available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("contactAvailability.read", availability)
    return availability
