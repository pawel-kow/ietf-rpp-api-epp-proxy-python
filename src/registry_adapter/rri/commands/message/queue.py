"""QUEUE-READ and QUEUE-DELETE. Every RRI message is a service notice that names its type and the domains and handles
it is about (gap Q15); RPP has no typed message for what RRI reports."""
from dataclasses import fields
from datetime import timezone

from core.model.message.message_queue import MessageQueue
from core.model.message.queue_message import QueueMessage
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.shared.rri_command import data_of, run
from registry_adapter.rri.xml.generated.message_5_0 import Delete, Message, QueueRead

HEADER = ("msgid", "msgcnt", "msgtime")


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


def _queue(transaction) -> MessageQueue:
    message = data_of(transaction, Message)
    if message is None:
        return MessageQueue(queue_size=0)
    kind, data = next(((f.metadata.get("name", f.name), getattr(message, f.name))
                       for f in fields(message) if f.name not in HEADER and getattr(message, f.name) is not None),
                      ("message", None))
    names = _names(data)
    created = message.msgtime.to_datetime().astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ") \
        if message.msgtime else None
    return MessageQueue(queue_size=message.msgcnt, message=QueueMessage(
        id=message.msgid, creationDate=created, lang=None,
        text=f"RRI {kind}" + (f": {', '.join(names)}" if names else "")))


def rri_queue_read(client, client_transaction_id=None):
    """The oldest message of the queue, and how many there are. The answer has the result code an RPP client knows
    from a poll: 1301 with a message, 1300 without."""
    resp = run(client, client_transaction_id, write=False, payload_of=_queue, queue_read=QueueRead())
    if isinstance(resp, ErrorResponse):
        return resp
    resp.code = (ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE if resp.payload.message is not None
                 else ResultCode.COMMAND_COMPLETED_NO_MESSAGES)
    return resp


def rri_queue_delete(client, message_id: str, client_transaction_id=None):
    """Deletes a message. RRI deletes only the oldest one (63650063607)."""
    return run(client, client_transaction_id, write=False, payload_of=lambda t: MessageQueue(queue_size=None),
               registry_denic_de_msg_5_0_delete=Delete(msgid=message_id))
