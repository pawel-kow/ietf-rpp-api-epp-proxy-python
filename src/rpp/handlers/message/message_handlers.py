import logging
import re

from connexion import ProblemException
from flask import Response

from core.flows.message.message_flows import read_message
from core.model.message.message_error_response import MessageErrorResponse
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from rpp.http.context import get_backend
from rpp.http.headers import client_transaction_id, generate_rpp_response_headers, problem_headers
from rpp.http.operation import require_empty_body, rpp_operation
from rpp.http.problem import raise_registry_error

from rpp.mapping.message import messages
logger = logging.getLogger("uvicorn.error")

XML_FORBIDDEN = re.compile("[^\u0009\u000a\u000d\u0020-\ud7ff\ue000-\ufffd\U00010000-\U0010ffff]")
LANGUAGE_TAG = re.compile(r"[A-Za-z]{1,8}(-[A-Za-z0-9]{1,8})*")


def _queue_size(value) -> str | None:
    """Core §6.2: an integer of at least 0."""
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return str(value)
    return None


def _language(value) -> str | None:
    """The language of the EPP message, when it can be a Content-Language value (BCP 47 syntax)."""
    if not value:
        return None
    if LANGUAGE_TAG.fullmatch(value):
        return value
    logger.warning("The language of a poll message is not a language tag, and is not sent")
    return None


def _headers(resp, language=None) -> dict:
    """Core §6.2: RPP-Queue-Size is the size of the queue the reply reported, and the language is the message's."""
    headers = generate_rpp_response_headers(resp)
    size = _queue_size(resp.payload.queue_size)
    if size is not None:
        headers["RPP-Queue-Size"] = size
    if _language(language):
        headers["Content-Language"] = language
    return headers


def _raise(resp: ErrorResponse):
    """An error of a message operation, which reports the size of the queue when it knows it."""
    try:
        raise_registry_error(resp)
    except ProblemException as problem:
        size = _queue_size(resp.queue_size) if isinstance(resp, MessageErrorResponse) else None
        if size is not None:
            problem.headers = {**(problem.headers or {}), "RPP-Queue-Size": size}
        raise


def _require_valid_id(id: str):
    """The id goes into XML, so it must be text XML 1.0 allows (its Char production), which a lone surrogate, U+FFFE and most control characters are not."""
    if not id or XML_FORBIDDEN.search(id):
        raise ProblemException(
            status=400, title=ResultCode.PARAMETER_VALUE_SYNTAX_ERROR.value[1], detail="The message id is not valid",
            headers=problem_headers(ResultCode.PARAMETER_VALUE_SYNTAX_ERROR),
        )


@rpp_operation
def messages_query():
    """EPP poll req. The EPP Compatibility Profile ignores `type` (core §16.10.1)."""
    resp = get_backend().messages.poll(client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        _raise(resp)
    if resp.payload.message is None:
        return [], 200, _headers(resp)
    return [messages.model_to_rpp(resp.payload.message)], 200, _headers(resp, resp.payload.message.lang)


@rpp_operation
def messages_read(id):
    _require_valid_id(id)
    resp = read_message(get_backend(), id, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        _raise(resp)
    return messages.model_to_rpp(resp.payload.message), 200, _headers(resp, resp.payload.message.lang)


@rpp_operation
def messages_delete(id):
    """EPP poll ack."""
    require_empty_body()
    _require_valid_id(id)
    resp = get_backend().messages.ack(id, client_transaction_id=client_transaction_id())
    if isinstance(resp, ErrorResponse):
        _raise(resp)
    headers = _headers(resp)
    del headers["Content-Type"]  # core §16.10.2: no content, and the OpenAPI defines none
    response = Response(status=200, headers=headers)
    response.headers.pop("Content-Type", None)  # Flask adds a default type to an empty response
    return response


@rpp_operation
def messages_create():
    """Only the server creates messages, and EPP has no command to insert one."""
    raise ProblemException(
        status=501, title=ResultCode.UNIMPLEMENTED_COMMAND.value[1],
        detail="EPP has no command to create a message",
        headers=problem_headers(ResultCode.UNIMPLEMENTED_COMMAND),
    )
