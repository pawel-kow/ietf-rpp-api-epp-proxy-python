from core.model.shared.availability import Availability
from rpp.dto.rpp_domain_name_availability import RPPDomainNameAvailability
from rpp.mapping.shared.common import reject_set
from rpp.schema.validator import validate_schema


def rpp_to_model(u_name: str | None, lgr: str | None) -> None:
    """Checks the query parameters of an availability check. EPP check takes the name alone, so `uName` and `lgr`
    are refused: draft-obispo-epp-idn-04 adds nothing to check."""
    reject_set(uName=u_name, lgr=lgr)


def model_to_rpp(check: Availability) -> dict:
    availability = RPPDomainNameAvailability(available=check.available, reason=None if check.available else check.reason).to_rpp()
    validate_schema("domainNameAvailability.read", availability)
    return availability
