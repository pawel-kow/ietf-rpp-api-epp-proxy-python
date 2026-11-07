from dataclasses import dataclass
from typing import Optional

from .queue_message import QueueMessage
from .response import OperationResponse


@dataclass(kw_only=True)
class PollResponse(OperationResponse):
    """The reply to a poll request: no message when the queue is empty."""
    queue_size: Optional[int]
    message: Optional[QueueMessage]
