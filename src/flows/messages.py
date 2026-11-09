from typing import Union

from eppclient.epp_messages import epp_messages_Poll
from eppclient.eppclient import EPPClient
from models import ErrorResponse, MessageErrorResponse, PollResponse, ResultCode


def read_message(epp_client: EPPClient, message_id: str, client_transaction_id=None) -> Union[PollResponse, ErrorResponse]:
    """Reads a message by id, which EPP allows only for the head of the queue.

    EPP cannot read past the head, so a queued message that is not the head, an acknowledged one and
    an unknown one look the same, and none of them can be answered.
    """
    resp = epp_messages_Poll(epp_client, client_transaction_id)
    if isinstance(resp, ErrorResponse):
        return resp
    if resp.message is None:
        return MessageErrorResponse(
            queue_size=resp.queue_size, code=ResultCode.OBJECT_DOES_NOT_EXIST, msg=f"Message {message_id} does not exist",
            server_transaction_id=resp.server_transaction_id, client_transaction_id=resp.client_transaction_id,
        )
    if resp.message.id != message_id:
        return MessageErrorResponse(
            queue_size=resp.queue_size, code=ResultCode.UNIMPLEMENTED_OPTION,
            msg="EPP can read only the message at the head of the queue, and message {id} is not it".format(id=message_id),
            server_transaction_id=resp.server_transaction_id, client_transaction_id=resp.client_transaction_id,
        )
    return resp
