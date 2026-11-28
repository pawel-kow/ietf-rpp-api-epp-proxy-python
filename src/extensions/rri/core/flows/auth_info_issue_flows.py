from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID, RriGateways


def create_auth_info_issue(backend: RegistryBackend, name: str,
                           client_transaction_id) -> OperationResponse[None] | ErrorResponse:
    """Asks the registry to issue authorisation information for the domain name, for any authenticated client."""
    gateways: RriGateways = backend.extension(EXTENSION_ID)
    return gateways.auth_info_issues.create(name, client_transaction_id=client_transaction_id)
