from dataclasses import dataclass
from typing import Optional

from core.model.message.queue_message import QueueMessage


@dataclass(kw_only=True)
class MessageQueue:
    """The message queue of a client as a reply reports it: its size, when the reply reported it, and the message at
    its head, when the reply carries one."""
    queue_size: Optional[int]
    message: Optional[QueueMessage] = None
