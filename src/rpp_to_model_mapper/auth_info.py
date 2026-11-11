from models import AuthInfo, AuthInfoIntent
from . import include_elements
from .common import parse_rpp
from .not_supported_by_epp import NotSupportedByEpp
from .rpp_models import RPPAuthInfo

AUTHINFO_METHOD = "authinfo"
AUTH_INFO = "authInfo"


def rpp_to_model(rpp: RPPAuthInfo | None) -> AuthInfo | None:
    if rpp is None:
        return None
    if rpp.method != AUTHINFO_METHOD:
        raise NotSupportedByEpp(f"authInfo method '{rpp.method}'")
    return AuthInfo(pw=rpp.authdata)


def model_to_rpp(auth_info: AuthInfo | None) -> RPPAuthInfo | None:
    if auth_info is None or not auth_info.pw:
        return None
    return RPPAuthInfo(method=AUTHINFO_METHOD, authdata=auth_info.pw)


def full_update_intent(object_identifier: str, rpp: dict, requested: frozenset[str]) -> AuthInfoIntent:
    """What a full update does with `authInfo`, which has onDemand Visibility: unless the request includes it, it is
    not part of the representation and is left alone. An included one is set when present and cleared when omitted."""
    if AUTH_INFO in include_elements.left_alone(object_identifier, rpp, requested):
        return AuthInfoIntent.keep()
    if AUTH_INFO not in rpp:
        return AuthInfoIntent.clear()
    return AuthInfoIntent.set(rpp_to_model(parse_rpp(RPPAuthInfo, rpp[AUTH_INFO])))
