from dataclasses import dataclass
from typing import Optional

from .pending_action_event import PendingActionEvent
from .transfer_event import TransferEvent


@dataclass(kw_only=True)
class QueueMessage:
    """The message at the head of the queue.

    `event` is None for a message without a structure the proxy can translate. `unmapped` then
    names what was left out, so the message can still be read and acknowledged.
    """
    id: str
    creationDate: Optional[str]
    lang: Optional[str]
    text: str
    event: Optional[TransferEvent | PendingActionEvent] = None
    unmapped: Optional[str] = None
