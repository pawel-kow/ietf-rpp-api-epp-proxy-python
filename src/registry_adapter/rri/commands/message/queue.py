"""QUEUE-READ and QUEUE-DELETE. A notification the proxy has a message type for becomes its event, any other a text that names
its type and the domains and handles it is about (a service notice, which can still be read and acknowledged)."""
import logging
from dataclasses import fields

from core.model.message.message_queue import MessageQueue
from core.model.message.queue_message import QueueMessage
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.commands.shared.rri_time import utc_time
from registry_adapter.rri.message_type import RriMessageType
from registry_adapter.rri.xml.generated.message_5_0 import Delete, EmptyType, Message, MsgTypeType, QueueRead

logger = logging.getLogger("uvicorn.error")

HEADER = ("msgid", "msgcnt", "msgtime")

NOT_THE_OLDEST = "63650063607"


def _names(value) -> list[str]:
    """The domain names and handles in a message's data, and nothing else of it: the rest can be personal."""
    if value is None or isinstance(value, (bool, int, float)):
        return []
    if isinstance(value, str):
        return []
    if isinstance(value, list):
        return [name for item in value for name in _names(item)]
    names = []
    for f in fields(value) if hasattr(value, "__dataclass_fields__") else []:
        item = getattr(value, f.name)
        if f.name in ("handle", "ace") and isinstance(item, str):
            names.append(item)
        elif f.name == "handle" and isinstance(item, list):
            names += [h for h in item if isinstance(h, str)]
        elif f.name != "message":
            names += _names(item)
    return list(dict.fromkeys(names))


def message_kind(message: Message) -> tuple[str, object]:
    """The `msgType` of a message and the element that holds its data."""
    return next(((f.metadata.get("name", f.name), getattr(message, f.name))
                 for f in fields(message) if f.name not in HEADER and getattr(message, f.name) is not None), ("message", None))


def queue_message(message: Message, types: dict[MsgTypeType, RriMessageType]) -> QueueMessage:
    """The message as the core model holds it: the event its message type translates it to, or the notice text only, where the
    proxy has no type for it or the XML lacks what the type needs."""
    kind, data = message_kind(message)
    names = _names(data)
    text = f"RRI {kind}" + (f": {', '.join(names)}" if names else "")
    created = utc_time(message.msgtime) if message.msgtime else None
    queued = QueueMessage(id=message.msgid, creationDate=created, lang=None, text=text, data_name=kind)
    message_type = next((t for msg_type, t in types.items() if msg_type.value == kind), None)
    if message_type is not None:
        try:
            queued.event = message_type.translate(message)
        except (AttributeError, TypeError, ValueError) as e:
            logger.warning("RRI message %r (%s) is a service notice, its data does not map: %s", message.msgid, kind, type(e).__name__)
            queued.unmapped = f"{kind}, which does not map"
    return queued


def rri_queue_read(client, client_transaction_id=None, msg_type: MsgTypeType | None = None) -> OperationResponse | ErrorResponse:
    """QUEUE-READ, of the oldest message of the queue or of a type. The payload is the XML `Message` (None for an empty queue)."""
    return run(client, client_transaction_id, write=False, payload_of=lambda transaction: data_of(transaction, Message),
               queue_read=QueueRead(value=EmptyType.VALUE, msg_type=msg_type))


def queue_of(resp: OperationResponse, types: dict[MsgTypeType, RriMessageType]) -> OperationResponse:
    """The answer a poll has: the result code an RPP client knows from a poll (1301 with a message, 1300 without), and the queue."""
    message = resp.payload
    resp.payload = MessageQueue(queue_size=message.msgcnt if message is not None else 0,
                                message=queue_message(message, types) if message is not None else None)
    resp.code = (ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE if message is not None
                 else ResultCode.COMMAND_COMPLETED_NO_MESSAGES)
    return resp


def rri_queue_delete(client, message_id: str, client_transaction_id=None, msg_type: MsgTypeType | None = None):
    """Deletes a message. RRI deletes only the oldest one, of the queue or of the type (63650063607)."""
    return run(client, client_transaction_id, write=False, payload_of=lambda t: MessageQueue(queue_size=None),
               registry_denic_de_msg_5_0_delete=Delete(value=EmptyType.VALUE, msgid=message_id, msg_type=msg_type))
