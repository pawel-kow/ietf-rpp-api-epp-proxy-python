from dataclasses import dataclass

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class PartiallyApplied(OperationResponse):
    """The answer to a request a backend runs as several commands, of which it applied the first and refused a later
    one, the `refusal`. The object changed, though not as asked: the code and transaction ids are the first command's,
    and the flows answer it as accepted, without the read-back that would show a state the client did not ask for."""
    refusal: ErrorResponse
