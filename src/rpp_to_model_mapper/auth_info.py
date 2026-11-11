from models import AuthInfo
from .not_supported_by_backend import NotSupportedByBackend
from .rpp_models import RPPAuthInfo

AUTHINFO_METHOD = "authinfo"


def rpp_to_model(rpp: RPPAuthInfo | None) -> AuthInfo | None:
    if rpp is None:
        return None
    if rpp.method != AUTHINFO_METHOD:
        raise NotSupportedByBackend(f"authInfo method '{rpp.method}'")
    return AuthInfo(pw=rpp.authdata)


def model_to_rpp(auth_info: AuthInfo | None) -> RPPAuthInfo | None:
    if auth_info is None or not auth_info.pw:
        return None
    return RPPAuthInfo(method=AUTHINFO_METHOD, authdata=auth_info.pw)

