from core.result.result_code import ResultCode
from extensions.rri.core.model.auth_info_setting import AuthInfoSetting
from registry_adapter.rri.commands.domain.auth_info import rri_create_auth_info1

# The registry refuses an `expire` it does not allow: after its limit of the lifetime, or on some dates within it (#134).
EXPIRE_REFUSED = {
    "63391068618": ResultCode.PARAMETER_VALUE_RANGE_ERROR,
    "63391068603": ResultCode.PARAMETER_VALUE_RANGE_ERROR,
}


def rri_auth_info_process_create(client, setting: AuthInfoSetting, client_transaction_id=None):
    """CREATE-AUTHINFO1 with the expiry date as `expire` (`YYYYMMDD`), none for the registry's default lifetime."""
    expire = setting.expiry_date.strftime("%Y%m%d") if setting.expiry_date else None
    return rri_create_auth_info1(client, setting.name, setting.password, client_transaction_id, expire=expire,
                                 codes=EXPIRE_REFUSED)
