from core.model.contact.contact_check_response import ContactCheckResponse
from rpp_schema_validator import validate_schema
from .rpp_models import RPPContactAvailability


def model_to_rpp(check: ContactCheckResponse) -> dict:
    availability = RPPContactAvailability(available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("contactAvailability.read", availability)
    return availability
