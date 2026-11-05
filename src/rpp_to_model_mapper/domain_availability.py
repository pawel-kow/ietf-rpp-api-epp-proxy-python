from models import DomainCheckResponseSingle
from rpp_schema_validator import validate_schema
from .rpp_models import RPPDomainNameAvailability


def model_to_rpp(check: DomainCheckResponseSingle) -> dict:
    availability = RPPDomainNameAvailability(available=check.available, reason=check.reason).to_rpp()
    validate_schema("domainNameAvailability.read", availability)
    return availability
