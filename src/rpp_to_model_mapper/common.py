from dataclasses_json.undefined import UndefinedParameterError

from models import AuthInfo, ProvisioningObject
from .rpp_models import RPPAuthInfo, RPPPatchOperation, RPPProvMetadata, RPPStatus
from .unsupported_rpp_feature import UnsupportedRppFeature

AUTHINFO_METHOD = "authinfo"


def parse_rpp(rpp_class, rpp: dict):
    """Builds the RPP object, rejecting undeclared properties (json draft §4.9.1)."""
    try:
        return rpp_class.from_dict(rpp)
    except UndefinedParameterError as e:
        raise ValueError(f"Undeclared property: {e}") from e


def reject_set(**members):
    """Rejects the named members when the request gives them a value."""
    for name, value in members.items():
        if value:
            raise UnsupportedRppFeature(f"'{name}' is not supported")


def reject_operation(operation: RPPPatchOperation):
    raise UnsupportedRppFeature(f"'{operation.op}' on '{operation.path}' is not supported")


def rpp_to_auth_info(rpp: RPPAuthInfo | None) -> AuthInfo | None:
    if rpp is None:
        return None
    if rpp.method != AUTHINFO_METHOD:
        raise UnsupportedRppFeature(f"authInfo method '{rpp.method}' is not supported")
    return AuthInfo(pw=rpp.authdata)


def auth_info_to_rpp(auth_info: AuthInfo | None) -> RPPAuthInfo | None:
    if auth_info is None or not auth_info.pw:
        return None
    return RPPAuthInfo(method=AUTHINFO_METHOD, authdata=auth_info.pw)


def prov_metadata_to_rpp(obj: ProvisioningObject) -> RPPProvMetadata:
    return RPPProvMetadata(
        spClientId=obj.clID,
        crClientId=obj.crID,
        crDate=obj.crDate,
        upDate=obj.upDate,
        trDate=obj.trDate,
    )


def statuses_to_rpp(obj: ProvisioningObject, status_type: str) -> list[RPPStatus]:
    return [RPPStatus(at_type=status_type, label=label) for label in obj.status or []]
