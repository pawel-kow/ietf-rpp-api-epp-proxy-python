from typing import Union

from core.model.message.message_error_response import MessageErrorResponse
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from core.ports.registry_backend import RegistryBackend
from core.model.message.message_queue import MessageQueue
from core.result.operation_response import OperationResponse


def read_message(backend: RegistryBackend, message_id: str, client_transaction_id=None) -> Union[OperationResponse[MessageQueue], ErrorResponse]:
    """Reads a message by id, which EPP allows only for the head of the queue.

    EPP cannot read past the head, so a queued message that is not the head, an acknowledged one and
    an unknown one look the same, and none of them can be answered.
    """
    resp = backend.messages.poll(client_transaction_id=client_transaction_id)
    if isinstance(resp, ErrorResponse):
        return resp
    if resp.payload.message is None:
        return MessageErrorResponse(
            queue_size=resp.payload.queue_size, code=ResultCode.OBJECT_DOES_NOT_EXIST, msg=f"Message {message_id} does not exist",
            server_transaction_id=resp.server_transaction_id, client_transaction_id=resp.client_transaction_id,
        )
    if resp.payload.message.id != message_id:
        return MessageErrorResponse(
            queue_size=resp.payload.queue_size, code=ResultCode.UNIMPLEMENTED_OPTION,
            msg="EPP can read only the message at the head of the queue, and message {id} is not it".format(id=message_id),
            server_transaction_id=resp.server_transaction_id, client_transaction_id=resp.client_transaction_id,
        )
    return resp
