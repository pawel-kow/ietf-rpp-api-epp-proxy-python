from dataclasses import dataclass
from typing import Optional

from core.result.error_response import ErrorResponse


@dataclass(kw_only=True)
class MessageErrorResponse(ErrorResponse):
    """An error of a message operation, with the size of the queue when the reply reported it."""
    queue_size: Optional[int] = None
