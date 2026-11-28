import logging

from core.model.shared.common import AuthInfo
from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from extensions.rri.core.model.verification_process import VerificationProcess
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID, RriGateways

logger = logging.getLogger(__name__)


def _error(code: ResultCode, msg: str, info: OperationResponse, client_transaction_id) -> ErrorResponse:
    return ErrorResponse(code=code, msg=msg, server_transaction_id=info.server_transaction_id,
                         client_transaction_id=client_transaction_id)


def read_verification_process(backend: RegistryBackend, name: str, authorization: AuthInfo | None,
                              client_transaction_id) -> OperationResponse[VerificationProcess] | ErrorResponse:
    """The verification process of a domain name. The sponsor sees all of it. Another client needs the Object Authorisation
    and sees the claims and the result of each record only, whatever the registry returned. A domain without a deadline
    has no process."""
    gateways: RriGateways = backend.extension(EXTENSION_ID)
    info = gateways.verification_processes.info(name, authorization, client_transaction_id=client_transaction_id)
    if isinstance(info, ErrorResponse):
        return info
    process = info.payload
    sponsor = (process.sponsor_id or "").lower() == backend.sponsor_id.lower()
    if not sponsor and authorization is None:
        return _error(ResultCode.AUTHORIZATION_ERROR,
                      "Only the sponsoring client, or a client with Object Authorisation, can read the verification",
                      info, client_transaction_id)
    if not process.exists:
        if process.hold_deadline or process.deletion_deadline:
            logger.warning("A domain has a verification deadline and no holder")
        return _error(ResultCode.OBJECT_DOES_NOT_EXIST, "The domain name has no verification process", info,
                      client_transaction_id)
    return OperationResponse(code=info.code, msg=info.msg, server_transaction_id=info.server_transaction_id,
                             client_transaction_id=client_transaction_id,
                             payload=process if sponsor else process.reduced())
