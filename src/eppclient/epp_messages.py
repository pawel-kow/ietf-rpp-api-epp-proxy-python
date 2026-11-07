import logging
from typing import Union

from epp_to_model_mapper import get_epp_error_response
from epp_to_model_mapper.messages import parse_ack_response, parse_poll_response, poll_ack_xml, poll_request_xml
from models import AckResponse, ErrorResponse, PollResponse, ResultCode
from .eppclient import EPPClient

logger = logging.getLogger("uvicorn.error")


def _error(response: str, client_transaction_id) -> ErrorResponse:
    """An EPP error. A reply with a code the proxy does not know is still an error, and not a crash."""
    try:
        return get_epp_error_response(response, client_transaction_id=client_transaction_id)
    except Exception as e:
        logger.warning("The EPP error reply of a poll cannot be read: %s", type(e).__name__)
        return ErrorResponse(
            code=ResultCode.COMMAND_FAILED, msg="The reply of the EPP server cannot be read",
            server_transaction_id=None, client_transaction_id=client_transaction_id,
        )


def epp_messages_Poll(epp_client: EPPClient, client_transaction_id=None) -> Union[PollResponse, ErrorResponse]:
    """
    Reads the message at the head of the queue of the registrar, with EPP poll req.
    Args:
        epp_client (EPPClient): The EPP client instance.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        PollResponse: The message, or none when the queue is empty.
    """
    success, code, response = epp_client.send_and_get_response(poll_request_xml(client_transaction_id))
    if success:
        return parse_poll_response(response, client_transaction_id=client_transaction_id)
    return _error(response, client_transaction_id)


def epp_messages_Ack(epp_client: EPPClient, message_id: str, client_transaction_id=None) -> Union[AckResponse, ErrorResponse]:
    """
    Acknowledges a message, which removes it from the queue, with EPP poll ack.
    Args:
        epp_client (EPPClient): The EPP client instance.
        message_id (str): The id of the message.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        AckResponse: The size of the queue after the acknowledgement.
    """
    success, code, response = epp_client.send_and_get_response(poll_ack_xml(message_id, client_transaction_id))
    if success:
        return parse_ack_response(response, client_transaction_id=client_transaction_id)
    return _error(response, client_transaction_id)
