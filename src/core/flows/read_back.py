from typing import Callable

from core.flows.mutation_result import MutationResult
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


def read_back(read: Callable[[str], object], key: str, mutation: OperationResponse, object_of: Callable) -> MutationResult:
    """Reads an object after a mutation the registry has already applied, with `read` (a gateway's `info`), and
    `object_of` takes the object from its answer.

    A failed readback must not look like a failed mutation. It uses its own clTRID: the client's is spent.
    """
    try:
        info = read(key)
    except Exception:
        return MutationResult(mutation=mutation)
    if isinstance(info, ErrorResponse):
        return MutationResult(mutation=mutation)
    return MutationResult(mutation=mutation, stored=object_of(info))
