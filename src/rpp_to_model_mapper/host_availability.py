from core.model.host.host_check_response import HostCheckResponse
from rpp_schema_validator import validate_schema
from .rpp_models import RPPHostAvailability


def model_to_rpp(check: HostCheckResponse) -> dict:
    availability = RPPHostAvailability(available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("hostAvailability.read", availability)
    return availability
