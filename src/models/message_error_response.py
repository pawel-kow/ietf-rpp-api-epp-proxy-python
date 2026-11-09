from dataclasses import dataclass
from typing import Optional

from .response import ErrorResponse


@dataclass(kw_only=True)
class MessageErrorResponse(ErrorResponse):
    """An error of a message operation, with the size of the queue when the reply reported it."""
    queue_size: Optional[int] = None
