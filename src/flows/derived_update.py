from eppclient.eppclient import EPPClient
from models import ErrorResponse, OperationResponse
from .replace_outcome import ReplaceOutcome
from .replacement_steps import ReplacementSteps


def replace(
    steps: ReplacementSteps, epp_client: EPPClient, key: str, wanted, client_transaction_id,
    current: OperationResponse | None = None,
) -> ReplaceOutcome | ErrorResponse:
    """A full update derived from EPP's partial one: the object is read unless the caller has `current`, the
    difference to the wanted state is taken, and sent as one update. Nothing is sent when nothing changes.
    The read and the update are not atomic."""
    if current is None:
        current = steps.read(epp_client, key)
        if isinstance(current, ErrorResponse):
            return current
    stored = steps.object_of(current)
    wanted = steps.prepare(wanted, stored)
    refused = steps.refuse(stored, wanted)
    if refused:
        return refused
    update = steps.difference(stored, wanted)
    if steps.changes_nothing(update):
        return ReplaceOutcome(current=current)
    mutation = steps.update(epp_client, update, client_transaction_id=client_transaction_id)
    if isinstance(mutation, ErrorResponse):
        return mutation
    return ReplaceOutcome(current=current, update=update, mutation=mutation)
