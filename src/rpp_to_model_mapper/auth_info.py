from models import AuthInfo
from .rpp_models import RPPAuthInfo
from .unsupported_rpp_feature import UnsupportedRppFeature

AUTHINFO_METHOD = "authinfo"


def rpp_to_model(rpp: RPPAuthInfo | None) -> AuthInfo | None:
    if rpp is None:
        return None
    if rpp.method != AUTHINFO_METHOD:
        raise UnsupportedRppFeature(f"authInfo method '{rpp.method}' is not supported")
    return AuthInfo(pw=rpp.authdata)


def model_to_rpp(auth_info: AuthInfo | None) -> RPPAuthInfo | None:
    if auth_info is None or not auth_info.pw:
        return None
    return RPPAuthInfo(method=AUTHINFO_METHOD, authdata=auth_info.pw)
