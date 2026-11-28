from typing import Protocol

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from extensions.rri.core.model.auth_info_process import AuthInfoProcess
from extensions.rri.core.model.auth_info_setting import AuthInfoSetting


class AuthInfoProcessGateway(Protocol):
    """The authorisation information of a domain name that its sponsor sets, reads and removes. `info` answers an
    `AuthInfoProcess` whose `expiry_date` is None for a domain that has none."""

    def create(self, setting: AuthInfoSetting, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...

    def info(self, name: str, client_transaction_id=None) -> OperationResponse[AuthInfoProcess] | ErrorResponse: ...

    def delete(self, name: str, client_transaction_id=None) -> OperationResponse[None] | ErrorResponse: ...
