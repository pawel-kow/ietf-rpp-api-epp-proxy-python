from connexion import ProblemException

import rpp_to_model_mapper as rpp_mapper
from eppclient.epp_messages import epp_messages_Ack, epp_messages_Poll
from flows import read_message
from models import ErrorResponse, ResultCode
from .auth import get_epp_client
from .helper.rpp_response import (
    client_transaction_id, generate_rpp_response_headers, problem_headers, raise_epp_error, require_empty_body,
    rpp_operation,
)


def _headers(resp, language=None) -> dict:
    """Core §6.2: RPP-Queue-Size is the size of the queue the reply reported, and the language is the message's."""
    headers = generate_rpp_response_headers(resp)
    if resp.queue_size is not None:
        headers["RPP-Queue-Size"] = str(resp.queue_size)
    if language:
        headers["Content-Language"] = language
    return headers


@rpp_operation
def messages_query():
    """EPP poll req. The EPP Compatibility Profile ignores `type` (core §16.10.1)."""
    resp = epp_messages_Poll(get_epp_client(), client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_epp_error(resp)
    if resp.message is None:
        return [], 200, _headers(resp)
    return [rpp_mapper.messages.model_to_rpp(resp.message)], 200, _headers(resp, resp.message.lang)


@rpp_operation
def messages_read(id):
    resp = read_message(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_epp_error(resp)
    return rpp_mapper.messages.model_to_rpp(resp.message), 200, _headers(resp, resp.message.lang)


@rpp_operation
def messages_delete(id):
    """EPP poll ack."""
    require_empty_body()
    resp = epp_messages_Ack(get_epp_client(), id, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        raise_epp_error(resp)
    headers = _headers(resp)
    del headers["Content-Type"]  # core §16.10.2: no content, and the OpenAPI defines none
    return None, 200, headers


@rpp_operation
def messages_create():
    """Only the server creates messages, and EPP has no command to insert one."""
    raise ProblemException(
        status=501, title=ResultCode.UNIMPLEMENTED_COMMAND.value[1],
        detail="EPP has no command to create a message",
        headers=problem_headers(ResultCode.UNIMPLEMENTED_COMMAND),
    )
