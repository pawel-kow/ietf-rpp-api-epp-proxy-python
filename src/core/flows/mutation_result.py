from dataclasses import dataclass
from typing import Generic, Optional, TypeVar

from core.result.operation_response import OperationResponse

T = TypeVar("T")


@dataclass(kw_only=True)
class MutationResult(Generic[T]):
    """A mutation the registry applied. `stored` is the object as read after it, None when it could not be read back."""
    mutation: OperationResponse
    stored: Optional[T] = None
