from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from core.result.result_code import ResultCode

T = TypeVar("T")


@dataclass(kw_only=True)
class OperationResponse(Generic[T]):
    """The answer of the registry to one command: its result, the transaction ids, and what it carries, the
    `payload` (None for a command that carries nothing back)."""
    code: ResultCode
    msg: str
    server_transaction_id: Optional[str]
    client_transaction_id: Optional[str]
    payload: Optional[T] = None
