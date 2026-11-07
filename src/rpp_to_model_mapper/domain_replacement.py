from models import DomainUpdate, DomainUpdateChange
from rpp_schema_validator import validate_schema
from . import auth_info, domain_patch_difference, patch_statuses
from .common import parse_rpp
from .domain_patch_difference import CHANGEABLE
from .rpp_models import RPPAuthInfo, RPPDomain

TYPE = "@type"
AUTH_INFO = "authInfo"
# The members a full update replaces. `authInfo` is left out: it is not compared, see `_auth_info_change`.
REPLACED = tuple(member for member in CHANGEABLE if member != AUTH_INFO)


def rpp_to_model(domain_name: str, rpp: dict) -> dict:
    """Checks a full update and returns it.

    A member outside `domainName.update` is rejected, also a create-only or a read-only one (json §4.4, core §16.8).
    """
    validate_schema("domainName.update", rpp)
    for member in rpp.keys() - {TYPE, *CHANGEABLE}:
        raise ValueError(f"'{member}' cannot be sent in a full update")
    parse_rpp(RPPDomain, {**rpp, "name": domain_name})  # rejects undeclared properties at any depth (json §4.9.1)
    return rpp


def _auth_info_change(rpp: dict) -> DomainUpdateChange | None:
    """A present `authInfo` always replaces the stored one. An omitted one is left alone: a client must not send
    `authInfo` (json §4.9.3), so a read back is no reason to clear it."""
    if AUTH_INFO not in rpp:
        return None
    return DomainUpdateChange(authInfo=auth_info.rpp_to_model(parse_rpp(RPPAuthInfo, rpp[AUTH_INFO])))


def rpp_to_model_with_current(domain_name: str, rpp: dict, current: dict) -> DomainUpdate:
    """The update that turns the current domain (its read representation) into the replacement.

    What the replacement omits is cleared, except the statuses of the server and the `authInfo`.
    """
    wanted = {
        **{member: value for member, value in current.items() if member not in REPLACED},
        **{member: rpp[member] for member in REPLACED if member in rpp and member != "status"},
        "status": rpp.get("status", []),
    }
    wanted = patch_statuses.with_server_statuses(wanted, current, "domainStatus")
    validate_schema("domainName.read", wanted)
    update = domain_patch_difference.difference(domain_name, current, wanted)
    update.change = _auth_info_change(rpp)
    return update
