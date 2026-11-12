from typing import Callable

from core.ports.replace_outcome import ReplaceOutcome
from core.ports.replacement_steps import ReplacementSteps
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode


def replace(
    steps: ReplacementSteps, key: str, wanted, client_transaction_id, current: OperationResponse | None = None,
) -> ReplaceOutcome | ErrorResponse:
    """A full update derived from a partial one: the object is read unless the caller has `current`, the
    difference to the wanted state is taken, and sent as one update. Nothing is sent when nothing changes.
    The read and the update are not atomic."""
    if current is None:
        current = steps.read(key)
        if isinstance(current, ErrorResponse):
            return current
    stored = current.payload
    wanted = steps.prepare(wanted, stored)
    refused = steps.refuse(stored, wanted)
    if refused:
        return refused
    update = steps.difference(stored, wanted)
    if steps.changes_nothing(update):
        return ReplaceOutcome(current=current)
    mutation = steps.update(update, client_transaction_id=client_transaction_id)
    if isinstance(mutation, ErrorResponse):
        return mutation
    return ReplaceOutcome(current=current, update=update, mutation=mutation)


def update(
    read: Callable, apply: Callable, replace: Callable, key: str, delta, client_transaction_id, sponsor_id: str,
    current: OperationResponse | None = None,
) -> OperationResponse | ErrorResponse:
    """A partial update derived from a full one, the mirror of `replace`, for a backend that updates by replacement
    only: the object is read unless the caller has `current`, the delta is applied to it with the object's `apply`,
    and the result replaces the object. When nothing changes nothing is sent, and only the sponsor (`sponsor_id`, the
    session's) is told so: another client gets the refusal the registry would have given. The read and the
    replacement are not atomic."""
    if current is None:
        current = read(key)
        if isinstance(current, ErrorResponse):
            return current
    outcome = replace(apply(current.payload, delta), current=current, client_transaction_id=client_transaction_id)
    if isinstance(outcome, ErrorResponse):
        return outcome
    if not outcome.unchanged:
        return outcome.mutation
    if (current.payload.clID or "").lower() != sponsor_id.lower():
        return ErrorResponse(
            code=ResultCode.AUTHORIZATION_ERROR, msg="Only the sponsoring client can update the object",
            server_transaction_id=current.server_transaction_id, client_transaction_id=client_transaction_id,
        )
    return OperationResponse(
        code=ResultCode.COMMAND_COMPLETED_SUCCESSFULLY, msg="Nothing to change",
        server_transaction_id=current.server_transaction_id, client_transaction_id=client_transaction_id,
    )
