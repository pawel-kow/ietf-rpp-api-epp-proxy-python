from dataclasses import replace
from typing import Union

from core.model.message.message_error_response import MessageErrorResponse
from core.model.message.message_queue import MessageQueue
from core.ports.registry_backend import RegistryBackend
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode


def read_message(backend: RegistryBackend, message_id: str, client_transaction_id=None) -> Union[OperationResponse[MessageQueue], ErrorResponse]:
    """Reads a message by id: the head of the queue, else the backend's `find`.

    A backend that cannot read past the head (`find` gives None) cannot tell a queued message that is not the head, an
    acknowledged one and an unknown one apart, and none of them can be answered.
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
        found = backend.messages.find(message_id, client_transaction_id=client_transaction_id)
        if isinstance(found, MessageErrorResponse) and found.queue_size is None:
            return replace(found, queue_size=resp.payload.queue_size)
        if isinstance(found, OperationResponse) and not isinstance(found, ErrorResponse):
            return replace(found, payload=replace(found.payload, queue_size=resp.payload.queue_size))  # the queue's, not the type's
        if found is not None:
            return found
        return MessageErrorResponse(
            queue_size=resp.payload.queue_size, code=ResultCode.UNIMPLEMENTED_OPTION,
            msg=f"{backend.profile.name} can read only the message at the head of the queue, and message {message_id} is not it",
            server_transaction_id=resp.server_transaction_id, client_transaction_id=resp.client_transaction_id,
        )
    return resp
