"""The Authorisation Information Process Object of the rri extension (docs/rri/rri-extension.md): the authorisation
information a sponsor sets for a domain name, with an optional expiry date."""
from datetime import date

from extensions.rri.core.model.auth_info_process import AuthInfoProcess
from extensions.rri.core.model.auth_info_setting import AuthInfoSetting
from extensions.rri.rpp.dto.rpp_auth_info_process import RPPAuthInfoProcess
from rpp.mapping.shared import auth_info
from rpp.mapping.shared.common import parse_rpp
from rpp.schema.validator import validate_request_schema, validate_schema


def rpp_to_model(name: str, rpp: dict, extensions: tuple[str, ...] = ()) -> AuthInfoSetting:
    """Converts a create request. A method other than `authinfo` is refused (`NotSupportedByBackend`, 501); the registry
    refuses an expiry date it does not allow, so none is checked here."""
    validate_request_schema("authInfoProcess.create", rpp, extensions)
    process = parse_rpp(RPPAuthInfoProcess, rpp)
    return AuthInfoSetting(name=name, password=auth_info.rpp_to_model(process.authInfo).pw,
                           expiry_date=date.fromisoformat(process.expiryDate) if process.expiryDate else None)


def model_to_rpp(process: AuthInfoProcess, extensions: tuple[str, ...] = ()) -> dict:
    """Converts the process to its read representation: the expiry date, never the authorisation information."""
    process_dict = RPPAuthInfoProcess(
        expiryDate=process.expiry_date.isoformat() if process.expiry_date else None).to_rpp()
    validate_schema("authInfoProcess.read", process_dict, extensions)
    return process_dict
