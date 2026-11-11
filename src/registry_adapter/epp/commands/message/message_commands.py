from typing import Union

from registry_adapter.epp.commands.message.message_xml import (
    parse_ack_response, parse_error_response, parse_poll_response, poll_ack_xml, poll_request_xml,
)
from core.result.error_response import ErrorResponse
from registry_adapter.epp.session.epp_client import EPPClient
from core.model.message.message_queue import MessageQueue
from core.result.operation_response import OperationResponse

def epp_messages_Poll(epp_client: EPPClient, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[MessageQueue], ErrorResponse]:
    """
    Reads the message at the head of the queue of the registrar, with EPP poll req.
    Args:
        epp_client (EPPClient): The EPP client instance.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[MessageQueue]: The message, or none when the queue is empty.
    """
    success, code, response = epp_client.send_and_get_response(poll_request_xml(client_transaction_id, ns_map=ns_map))
    if success:
        return parse_poll_response(response, client_transaction_id=client_transaction_id)
    return parse_error_response(response, client_transaction_id)


def epp_messages_Ack(epp_client: EPPClient, message_id: str, client_transaction_id=None, *, ns_map: dict[str, str]) -> Union[OperationResponse[MessageQueue], ErrorResponse]:
    """
    Acknowledges a message, which removes it from the queue, with EPP poll ack.
    Args:
        epp_client (EPPClient): The EPP client instance.
        message_id (str): The id of the message.
        client_transaction_id (str): The client transaction ID for the request.
    Returns:
        OperationResponse[MessageQueue]: The size of the queue after the acknowledgement.
    """
    success, code, response = epp_client.send_and_get_response(poll_ack_xml(message_id, client_transaction_id, ns_map=ns_map))
    if success:
        return parse_ack_response(response, client_transaction_id=client_transaction_id)
    return parse_error_response(response, client_transaction_id)
