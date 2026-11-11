from dataclasses import dataclass
from typing import Optional

from core.model.message.pending_action_event import PendingActionEvent
from core.model.message.transfer_event import TransferEvent


@dataclass(kw_only=True)
class QueueMessage:
    """The message at the head of the queue.

    `event` is None for a message without a structure the proxy can translate. `unmapped` then
    names what was left out, so the message can still be read and acknowledged. `data_name` is the
    qualified name of the data an `event` was made from, for a log when the event turns out unusable.
    """
    id: str
    creationDate: Optional[str]
    lang: Optional[str]
    text: str
    event: Optional[TransferEvent | PendingActionEvent] = None
    unmapped: Optional[str] = None
    data_name: Optional[str] = None
