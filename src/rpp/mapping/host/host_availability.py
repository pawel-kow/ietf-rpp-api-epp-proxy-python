from core.model.host.host_check_response import HostCheckResponse
from rpp.schema.validator import validate_schema
from rpp.dto.rpp_host_availability import RPPHostAvailability


def model_to_rpp(check: HostCheckResponse) -> dict:
    availability = RPPHostAvailability(available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("hostAvailability.read", availability)
    return availability
