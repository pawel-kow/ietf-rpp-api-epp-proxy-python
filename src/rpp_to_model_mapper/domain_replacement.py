from models import DomainReplacement
from registry import BackendProfile
from rpp_schema_validator import validate_schema
from . import auth_info, domain_wanted, include_elements
from .common import parse_rpp
from .domain_wanted import CHANGEABLE
from .rpp_models import RPPAuthInfo, RPPDomain

TYPE = "@type"
OBJECT = "domainName"
AUTH_INFO = "authInfo"


def rpp_to_model(
    domain_name: str, rpp: dict, requested: frozenset[str] = frozenset(), *, profile: BackendProfile,
) -> DomainReplacement:
    """Converts a full update to the domain it asks for. What it omits is cleared, except the data elements with
    onDemand Visibility that `requested` (the `includeElements` of the request) does not name.

    A member outside `domainName.update` is rejected, also a create-only or a read-only one (json §4.4, core §16.8).
    """
    validate_schema("domainName.update", rpp)
    for member in rpp.keys() - {TYPE, *CHANGEABLE}:
        raise ValueError(f"'{member}' cannot be sent in a full update")
    parse_rpp(RPPDomain, {**rpp, "name": domain_name})  # rejects undeclared properties at any depth (json §4.9.1)
    unchanged = include_elements.left_alone(OBJECT, rpp, requested)
    password = auth_info.rpp_to_model(parse_rpp(RPPAuthInfo, rpp[AUTH_INFO])) if AUTH_INFO in rpp else None
    return domain_wanted.rpp_to_model(domain_name, rpp, password, unchanged, profile=profile)
