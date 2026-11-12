from typing import Callable

from core.flows.mutation_result import MutationResult
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.partially_applied import PartiallyApplied


def read_back(read: Callable[[str], OperationResponse], key: str, mutation: OperationResponse) -> MutationResult:
    """Reads an object after a mutation the registry has already applied, with `read` (a gateway's `info`).

    A failed readback must not look like a failed mutation. It uses its own clTRID: the client's is spent.
    A mutation the backend applied only in part is not read back: the answer says it was accepted (202).
    """
    if isinstance(mutation, PartiallyApplied):
        return MutationResult(mutation=mutation)
    try:
        info = read(key)
    except Exception:
        return MutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return MutationResult(mutation=mutation)
    return MutationResult(mutation=mutation, stored=info.payload)
