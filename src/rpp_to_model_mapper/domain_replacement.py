from models import DomainReplacement
from rpp_schema_validator import validate_schema
from . import auth_info, domain_wanted
from .common import parse_rpp
from .domain_wanted import CHANGEABLE
from .rpp_models import RPPDomain

TYPE = "@type"
OBJECT = "domainName"


def rpp_to_model(domain_name: str, rpp: dict, requested: frozenset[str] = frozenset()) -> DomainReplacement:
    """Converts a full update to the domain it asks for. What it omits is cleared, except the data elements with
    onDemand Visibility that `requested` (the `includeElements` of the request) does not name.

    A member outside `domainName.update` is rejected, also a create-only or a read-only one (json §4.4, core §16.8).
    """
    validate_schema("domainName.update", rpp)
    for member in rpp.keys() - {TYPE, *CHANGEABLE}:
        raise ValueError(f"'{member}' cannot be sent in a full update")
    parse_rpp(RPPDomain, {**rpp, "name": domain_name})  # rejects undeclared properties at any depth (json §4.9.1)
    return domain_wanted.rpp_to_model(domain_name, rpp, auth_info.full_update_intent(OBJECT, rpp, requested))
