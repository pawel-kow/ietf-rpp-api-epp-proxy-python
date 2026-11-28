import logging

from core.flows.mutation_result import MutationResult
from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from extensions.rri.core.model.auth_info_process import AuthInfoProcess
from extensions.rri.core.model.auth_info_setting import AuthInfoSetting
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID, RriGateways

logger = logging.getLogger(__name__)


def _gateways(backend: RegistryBackend) -> RriGateways:
    return backend.extension(EXTENSION_ID)


def create_auth_info_process(backend: RegistryBackend, setting: AuthInfoSetting,
                             client_transaction_id) -> MutationResult[AuthInfoProcess] | ErrorResponse:
    """Sets the authorisation information and reads back the expiry date that applies. A read-back that fails does not
    fail the create, which the registry has applied: the answer then has the date the client asked for, if any."""
    gateway = _gateways(backend).auth_info_processes
    created = gateway.create(setting, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    try:
        info = gateway.info(setting.name)
    except Exception:  # noqa: BLE001 - the create is applied
        logger.warning("The read-back of the authorisation information failed after the create")
        info = None
    if info is None or isinstance(info, ErrorResponse) or info.payload.expiry_date is None:
        if info is not None and isinstance(info, ErrorResponse):
            logger.warning("The read-back of the authorisation information failed with %s", info.code.value[0])
        return MutationResult(mutation=created, stored=AuthInfoProcess(expiry_date=setting.expiry_date))
    return MutationResult(mutation=created, stored=info.payload)


def read_auth_info_process(backend: RegistryBackend, name: str,
                           client_transaction_id) -> OperationResponse[AuthInfoProcess] | ErrorResponse:
    """The expiry date of the authorisation information. Only the sponsor may read it, and a domain without it has no
    such process."""
    info = _gateways(backend).auth_info_processes.info(name, client_transaction_id=client_transaction_id)
    if isinstance(info, ErrorResponse):
        return info
    if (info.payload.sponsor_id or "").lower() != backend.sponsor_id.lower():
        return ErrorResponse(code=ResultCode.AUTHORIZATION_ERROR,
                             msg="Only the sponsoring client can read the authorisation information",
                             server_transaction_id=info.server_transaction_id,
                             client_transaction_id=client_transaction_id)
    if not info.payload.exists:
        return ErrorResponse(code=ResultCode.OBJECT_DOES_NOT_EXIST, msg="The domain name has no authorisation information",
                             server_transaction_id=info.server_transaction_id,
                             client_transaction_id=client_transaction_id)
    return info


def delete_auth_info_process(backend: RegistryBackend, name: str,
                             client_transaction_id) -> OperationResponse[None] | ErrorResponse:
    return _gateways(backend).auth_info_processes.delete(name, client_transaction_id=client_transaction_id)
