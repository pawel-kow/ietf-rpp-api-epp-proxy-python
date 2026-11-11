from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode


def require_sponsor(
    backend: RegistryBackend, sponsor_id: str | None, read: OperationResponse, client_transaction_id, object_name: str,
) -> ErrorResponse | None:
    """The refusal of an update that changes nothing, which sends no command. Only the sponsor may update
    (data-objects §11.3.4, §12.3.4), and the registry would have said so. The backend's sponsor id is compared
    whatever its case."""
    if (sponsor_id or "").lower() == backend.sponsor_id.lower():
        return None
    return ErrorResponse(
        code=ResultCode.AUTHORIZATION_ERROR,
        msg=f"Only the sponsoring client can update the {object_name}",
        server_transaction_id=read.server_transaction_id,
        client_transaction_id=client_transaction_id,
    )
