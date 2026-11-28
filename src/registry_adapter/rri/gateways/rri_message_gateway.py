import uuid
from dataclasses import replace

from core.model.message.message_error_response import MessageErrorResponse
from core.model.message.message_queue import MessageQueue
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.message.queue import NOT_THE_OLDEST, queue_of, rri_queue_delete, rri_queue_read
from registry_adapter.rri.commands.message.transfer_outcome import TRANSFER_OUTCOME
from registry_adapter.rri.commands.shared.rri_time import utc_moment
from registry_adapter.rri.extension_part import RriExtensionPart
from registry_adapter.rri.xml.generated.message_5_0 import MsgTypeType


class RriMessageGateway:
    """The message queue of an RRI RegAcc. The message types it reads are the transfer outcome and those the extension parts have.

    RRI reads the oldest message of the queue or of one `msgType`, and deletes the oldest one of the queue or of a `msgType`
    (QUEUE-READ and QUEUE-DELETE cost no quota). So a Query by type reads once per type, and a message that is not the
    oldest of the queue is found by reading the head of each `msgType`.
    """

    def __init__(self, client, extension_parts: list[RriExtensionPart] = ()):
        self.client = client
        message_types = [TRANSFER_OUTCOME, *(t for part in extension_parts for t in part.message_types)]
        self._by_identifier = {t.identifier: t for t in message_types}
        self._types = {t.msg_type: t for t in message_types}

    def poll(self, client_transaction_id=None, message_types=None):
        """Without types the oldest message. With types the oldest of those with a `msgType` (one read each, the oldest by
        `msgtime` wins), and the queue size is the sum of their counts. A type with no `msgType` reads nothing."""
        if message_types is None:
            resp = rri_queue_read(self.client, client_transaction_id)
            return resp if isinstance(resp, ErrorResponse) else queue_of(resp, self._types)
        wanted = [self._by_identifier[i].msg_type for i in dict.fromkeys(message_types) if i in self._by_identifier]
        if not wanted:
            return OperationResponse(code=ResultCode.COMMAND_COMPLETED_NO_MESSAGES, msg="Command completed successfully; no messages",
                                     server_transaction_id=str(uuid.uuid4()), client_transaction_id=client_transaction_id,
                                     payload=MessageQueue(queue_size=0))
        replies = []
        for msg_type in wanted:
            resp = rri_queue_read(self.client, client_transaction_id, msg_type)
            if isinstance(resp, ErrorResponse):
                return resp
            replies.append(resp)
        messages = [r.payload for r in replies if r.payload is not None]
        oldest = min(messages, key=lambda m: utc_moment(m.msgtime), default=None)
        resp = replies[-1]
        size = sum(r.payload.msgcnt or 0 for r in replies if r.payload is not None)
        resp.payload = oldest
        resp = queue_of(resp, self._types)
        resp.payload = replace(resp.payload, queue_size=size)
        return resp

    def _heading(self, message_id: str, client_transaction_id):
        """The reply of the `msgType` whose oldest message has the id, None when none has, or the error of a read."""
        for msg_type in MsgTypeType:
            resp = rri_queue_read(self.client, client_transaction_id, msg_type)
            if isinstance(resp, ErrorResponse):
                return resp
            if resp.payload is not None and resp.payload.msgid == message_id:
                return resp, msg_type
        return None

    def find(self, message_id: str, client_transaction_id=None):
        found = self._heading(message_id, client_transaction_id)
        if isinstance(found, ErrorResponse):
            return found
        if found is None:
            return MessageErrorResponse(code=ResultCode.OBJECT_DOES_NOT_EXIST, msg=f"Message {message_id} does not exist",
                                        server_transaction_id=str(uuid.uuid4()), client_transaction_id=client_transaction_id)
        return queue_of(found[0], self._types)

    def ack(self, message_id: str, client_transaction_id=None):
        """A QUEUE-DELETE of the oldest message of the queue. Where the registry says the message is not the oldest, the one that
        is the oldest of its `msgType` is deleted with it, if the id is."""
        resp = rri_queue_delete(self.client, message_id, client_transaction_id)
        if not (isinstance(resp, ErrorResponse) and resp.registry_code == NOT_THE_OLDEST):
            return resp
        found = self._heading(message_id, client_transaction_id)
        if isinstance(found, ErrorResponse):
            return found    # the failed read answers, as for `find`
        if found is None:
            return resp
        return rri_queue_delete(self.client, message_id, client_transaction_id, found[1])
