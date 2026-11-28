from core.flows.mutation_result import MutationResult
from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from extensions.rri.core.model.release import Release
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID, RriGateways


def create_release(backend: RegistryBackend, name: str, keep_nameservers: bool | None,
                   client_transaction_id) -> MutationResult[Release] | ErrorResponse:
    """Releases the domain name to the registry. Without a statement the name servers are kept; the result holds the
    value that applied."""
    gateways: RriGateways = backend.extension(EXTENSION_ID)
    keep = True if keep_nameservers is None else keep_nameservers
    released = gateways.releases.create(name, keep, client_transaction_id=client_transaction_id)
    if isinstance(released, ErrorResponse):
        return released
    return MutationResult(mutation=released, stored=Release(keep_nameservers=keep))
