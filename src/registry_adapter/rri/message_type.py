from dataclasses import dataclass
from typing import Callable

from registry_adapter.rri.xml.generated.message_5_0 import Message, MsgTypeType


@dataclass(frozen=True)
class RriMessageType:
    """A message type of RPP that an RRI notification (`msgType`) is read as: the identifier of the RPP message type (which a
    Query's `type` names), and how the XML message becomes the event the core model holds (a `TransferEvent`, or an
    `ExtensionEvent` of the extension that defines the type). The module of an extension (`registry_adapter.rri.extensions.<name>`)
    states its own as `MESSAGE_TYPES`."""
    msg_type: MsgTypeType
    identifier: str
    translate: Callable[[Message], object]
