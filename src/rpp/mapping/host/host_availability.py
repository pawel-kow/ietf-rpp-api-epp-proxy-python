from core.model.shared.availability import Availability
from rpp.dto.rpp_host_availability import RPPHostAvailability
from rpp.schema.validator import validate_schema


def model_to_rpp(check: Availability) -> dict:
    availability = RPPHostAvailability(available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("hostAvailability.read", availability)
    return availability
