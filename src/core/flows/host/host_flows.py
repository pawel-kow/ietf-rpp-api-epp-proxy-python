from typing import Callable

from core.model.host.host import Host
from core.model.host.host_replacement import HostReplacement
from core.model.host.host_update import HostUpdate
from core.result.error_response import ErrorResponse
from core.ports.registry_backend import RegistryBackend
from core.flows.mutation_result import MutationResult
from core.flows.read_back import read_back
from core.flows.sponsor import require_sponsor


def _read_back(backend: RegistryBackend, host_name: str, mutation) -> MutationResult:
    return read_back(backend.hosts.info, host_name, mutation)


def create_host(backend: RegistryBackend, host: Host, client_transaction_id) -> MutationResult | ErrorResponse:
    created = backend.hosts.create(host, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    return _read_back(backend, created.payload.name, created)


def update_host(backend: RegistryBackend, update: HostUpdate, client_transaction_id) -> MutationResult | ErrorResponse:
    updated = backend.hosts.update(update, client_transaction_id=client_transaction_id)
    if isinstance(updated, ErrorResponse):
        return updated
    return _read_back(backend, update.new_name or update.name, updated)


def _replaced(backend: RegistryBackend, outcome, client_transaction_id) -> MutationResult | ErrorResponse:
    """The answer to a full update: the host read back, or the host as read when nothing changed, for its sponsor."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    if outcome.unchanged:
        current = outcome.current
        refused = require_sponsor(backend, current.payload.clID, current, client_transaction_id, "host")
        return refused or MutationResult(mutation=current, stored=current.payload)
    return _read_back(backend, outcome.update.new_name or outcome.update.name, outcome.mutation)


def patch_host(
    backend: RegistryBackend,
    host_name: str,
    update: HostUpdate | None,
    wanted_from_current: Callable[[Host], HostReplacement],
    client_transaction_id,
) -> MutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current host (#71): it is read,
    `wanted_from_current` applies the patch, and the host is replaced with the result."""
    if update is not None:
        return update_host(backend, update, client_transaction_id)
    current = backend.hosts.info(host_name)
    if isinstance(current, ErrorResponse):
        return current
    outcome = backend.hosts.replace(
        wanted_from_current(current.payload), current=current, client_transaction_id=client_transaction_id,
    )
    return _replaced(backend, outcome, client_transaction_id)


def replace_host(backend: RegistryBackend, wanted: HostReplacement, client_transaction_id) -> MutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = backend.hosts.replace(wanted, client_transaction_id=client_transaction_id)
    return _replaced(backend, outcome, client_transaction_id)
