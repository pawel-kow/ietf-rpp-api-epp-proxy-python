from typing import Callable

from eppclient.epp_hosts import epp_hosts_Create, epp_hosts_Info, epp_hosts_Update
from eppclient.eppclient import EPPClient
from models import ErrorResponse, Host, HostReplacement, HostUpdate, OperationResponse, host_difference
from . import derived_update
from .host_mutation_result import HostMutationResult
from .replacement_steps import ReplacementSteps
from .sponsor import require_sponsor


def _read_back(epp_client: EPPClient, host_name: str, mutation: OperationResponse) -> HostMutationResult:
    """Reads the host after a mutation the registry has already applied.

    A failed readback must not look like a failed mutation. It uses its own clTRID: the client's is spent.
    """
    try:
        info = epp_hosts_Info(epp_client, host_name)
    except Exception:
        return HostMutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return HostMutationResult(mutation=mutation)
    return HostMutationResult(mutation=mutation, host=info.host)


def create_host(epp_client: EPPClient, host: Host, client_transaction_id) -> HostMutationResult | ErrorResponse:
    created = epp_hosts_Create(epp_client, host, client_transaction_id=client_transaction_id)
    if isinstance(created, ErrorResponse):
        return created
    return _read_back(epp_client, created.host.name, created)


def update_host(epp_client: EPPClient, update: HostUpdate, client_transaction_id) -> HostMutationResult | ErrorResponse:
    updated = epp_hosts_Update(epp_client, update, client_transaction_id=client_transaction_id)
    if isinstance(updated, ErrorResponse):
        return updated
    return _read_back(epp_client, update.new_name or update.name, updated)


HOST_STEPS = ReplacementSteps(
    read=epp_hosts_Info,
    object_of=lambda info: info.host,
    difference=host_difference.difference,
    changes_nothing=host_difference.changes_nothing,
    update=epp_hosts_Update,
)


def _replaced(epp_client: EPPClient, outcome, client_transaction_id) -> HostMutationResult | ErrorResponse:
    """The answer to a full update: the host read back, or the host as read when nothing changed, for its sponsor."""
    if isinstance(outcome, ErrorResponse):
        return outcome
    if outcome.unchanged:
        current = outcome.current
        refused = require_sponsor(epp_client, current.host.clID, current, client_transaction_id, "host")
        return refused or HostMutationResult(mutation=current, host=current.host)
    return _read_back(epp_client, outcome.update.new_name or outcome.update.name, outcome.mutation)


def patch_host(
    epp_client: EPPClient,
    host_name: str,
    update: HostUpdate | None,
    wanted_from_current: Callable[[Host], HostReplacement],
    client_transaction_id,
) -> HostMutationResult | ErrorResponse:
    """A partial update. Without an `update` the patch needs the current host (#71): it is read,
    `wanted_from_current` applies the patch, and the host is replaced with the result."""
    if update is not None:
        return update_host(epp_client, update, client_transaction_id)
    current = epp_hosts_Info(epp_client, host_name)
    if isinstance(current, ErrorResponse):
        return current
    outcome = derived_update.replace(
        HOST_STEPS, epp_client, host_name, wanted_from_current(current.host), client_transaction_id, current,
    )
    return _replaced(epp_client, outcome, client_transaction_id)


def replace_host(epp_client: EPPClient, wanted: HostReplacement, client_transaction_id) -> HostMutationResult | ErrorResponse:
    """A full update. A replacement that changes nothing sends no update (core §16.8 asks for a 200)."""
    outcome = derived_update.replace(HOST_STEPS, epp_client, wanted.name, wanted, client_transaction_id)
    return _replaced(epp_client, outcome, client_transaction_id)
