import logging
from typing import Union

from core.model.message.message_queue import MessageQueue
from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from registry_adapter.epp.commands.message.common import (
    count_of, decode, EPP_NS, parse_error_response, raw_header, unreadable,
)
from registry_adapter.epp.commands.shared.epp_response import cl_trid, parse_epp_response_header
from registry_adapter.epp.session.epp_client import EPPClient
from registry_adapter.epp.xml.codec import epp_to_str, str_to_epp
from registry_adapter.epp.xml.generated.epp_1_0 import CommandType, Epp, PollOpType, PollType

logger = logging.getLogger("uvicorn.error")


def poll_ack(message_id: str, rpp_cl_trid: str) -> Epp:
    return Epp(command=CommandType(poll=PollType(op=PollOpType.ACK, msg_id=message_id), cl_trid=rpp_cl_trid))


def poll_ack_xml(message_id: str, client_request_id=None, *, ns_map: dict[str, str]) -> str:
    return epp_to_str(poll_ack(message_id, cl_trid(client_request_id)), ns_map)


def parse_ack_response(xml_string: str, client_transaction_id: str | None) -> OperationResponse[MessageQueue] | ErrorResponse:
    """Parses the reply to poll ack, whose msgQ, when present, counts what is left.

    A reply without a readable result code is an error, as nothing says what happened to the message.
    """
    try:
        epp = str_to_epp(xml_string)
        header = parse_epp_response_header(epp)
        if client_transaction_id is None:
            header["client_transaction_id"] = None
        msg_q = epp.response.msg_q
        return OperationResponse(payload=MessageQueue(queue_size=None if msg_q is None else msg_q.count), **header)
    except Exception as e:
        logger.warning("Poll ack reply does not follow the EPP schema: %s", type(e).__name__)
        root = decode(xml_string)
        header = raw_header(root, client_transaction_id)
        if header is None:
            return unreadable(header, client_transaction_id)
        msg_q = root.find("./epp:response/epp:msgQ", EPP_NS)
        return OperationResponse(payload=MessageQueue(queue_size=None if msg_q is None else count_of(msg_q)), **header)


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
