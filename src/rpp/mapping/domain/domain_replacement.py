from core.capabilities.backend_profile import BackendProfile
from core.model.domain.domain_replacement import DomainReplacement
from rpp.dto.rpp_auth_info import RPPAuthInfo
from rpp.dto.rpp_domain import RPPDomain
from rpp.mapping.domain import domain_wanted
from rpp.mapping.domain.domain_members import DOMAIN_MEMBERS
from rpp.mapping.shared import auth_info, include_elements
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_request_schema, validate_schema

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
    validate_schema("domainName.update", rpp, extensions=profile.extensions)
    DOMAIN_MEMBERS.check(rpp, profile.extensions)    # before step 2: an extension's refusal is not a broken profile constraint
    validate_request_schema("domainName.update", rpp, extensions=profile.extensions)
    for member in rpp.keys() - {TYPE, *domain_wanted.changeable(profile)}:
        raise ValueError(f"'{member}' cannot be sent in a full update")
    base, _ = DOMAIN_MEMBERS.split(rpp, "domainName.update", profile.extensions)
    parse_rpp(RPPDomain, {**base, "name": domain_name})  # rejects undeclared properties at any depth (json §4.9.1)
    unchanged = include_elements.left_alone(OBJECT, rpp, requested)
    password = auth_info.rpp_to_model(parse_rpp(RPPAuthInfo, rpp[AUTH_INFO])) if AUTH_INFO in rpp else None
    return domain_wanted.rpp_to_model(domain_name, rpp, password, unchanged, profile=profile)
