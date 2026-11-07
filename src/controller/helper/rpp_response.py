import functools
import logging
import re
import uuid

from connexion import ProblemException, request
from flask import request as flask_request
from jsonschema import ValidationError

from models import ErrorResponse, OperationResponse, ResultCode
from rpp_to_model_mapper import UnsupportedRppFeature

logger = logging.getLogger("uvicorn.error")

PRINTABLE_ASCII = re.compile(r"[\x20-\x7e]+")
RPP_MEDIA_TYPE = "application/rpp+json"
RPP_ERROR_TYPE = "urn:ietf:params:rpp:error"

# Core §18.1 Table 9, for the codes the proxy can receive or produce.
STATUS_BY_RESULT = {
    ResultCode.COMMAND_USE_ERROR: 409,
    ResultCode.UNIMPLEMENTED_COMMAND: 501,
    ResultCode.UNIMPLEMENTED_OPTION: 501,
    ResultCode.UNIMPLEMENTED_EXTENSION: 501,
    ResultCode.BILLING_FAILURE: 402,
    ResultCode.OBJECT_NOT_ELIGIBLE_FOR_RENEWAL: 409,
    ResultCode.OBJECT_NOT_ELIGIBLE_FOR_TRANSFER: 409,
    ResultCode.AUTHENTICATION_ERROR: 401,
    ResultCode.AUTHORIZATION_ERROR: 403,
    ResultCode.INVALID_AUTHORIZATION_INFORMATION: 401,
    ResultCode.OBJECT_PENDING_TRANSFER: 409,
    ResultCode.OBJECT_NOT_PENDING_TRANSFER: 409,
    ResultCode.OBJECT_EXISTS: 409,
    ResultCode.OBJECT_DOES_NOT_EXIST: 404,
    ResultCode.OBJECT_STATUS_PROHIBITS_OPERATION: 409,
    ResultCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION: 409,
    ResultCode.PARAMETER_VALUE_POLICY_ERROR: 422,
    ResultCode.UNIMPLEMENTED_OBJECT_SERVICE: 501,
    ResultCode.DATA_MANAGEMENT_POLICY_VIOLATION: 422,
    ResultCode.AUTHENTICATION_ERROR_SERVER_CLOSING_CONNECTION: 401,
    ResultCode.SESSION_LIMIT_EXCEEDED_SERVER_CLOSING_CONNECTION: 429,
}


def client_transaction_id() -> str | None:
    return request.headers.get("RPP-Cltrid")


def rpp_code(code: ResultCode) -> str:
    """The RPP result code of an EPP code: EPP-derived codes have a leading 0 (core §18)."""
    return f"0{code.value[0]}"


def http_status(code: ResultCode) -> int:
    """Core §18.1: Table 9, then the class mapping of Table 10."""
    if code in STATUS_BY_RESULT:
        return STATUS_BY_RESULT[code]
    return 500 if code.value[0][1] in ("4", "5") else 400


def server_transaction_id_of(value: str | None) -> str:
    """RPP-Svtrid: the id of the EPP reply, when a header can carry it, otherwise a new one.

    The id comes from the backend, and a value with other than printable ASCII cannot be a header value.
    """
    if value and PRINTABLE_ASCII.fullmatch(value):
        return value
    if value:
        logger.warning("The server transaction id of the EPP reply is not printable ASCII, and is replaced")
    return str(uuid.uuid4())


def generate_rpp_response_headers(resp: OperationResponse) -> dict:
    """The headers of a successful response, with or without content."""
    return {
        "Content-Type": RPP_MEDIA_TYPE,
        "RPP-Cltrid": client_transaction_id(),
        "RPP-Svtrid": server_transaction_id_of(resp.server_transaction_id),
        "RPP-Code": rpp_code(resp.code),
    }


def problem_headers(code: ResultCode, server_transaction_id: str | None = None) -> dict:
    """The RPP headers of a Problem Detail, which has no EPP reply behind it unless given one."""
    return {
        "RPP-Svtrid": server_transaction_id_of(server_transaction_id),
        "RPP-Code": rpp_code(code),
    }


def raise_epp_error(resp: ErrorResponse):
    """Translates an EPP error into a Problem Detail."""
    raise ProblemException(
        status=http_status(resp.code),
        title=resp.code.value[1],
        detail=resp.msg,
        headers=problem_headers(resp.code, resp.server_transaction_id),
    )


def request_has_content() -> bool:
    """Whether the request carries content, whatever its framing, type or syntax: `null` and `{}` count.

    Read through Flask: Connexion's `get_body()` gives the parsed content, which is falsy for these,
    and waiting on the ASGI stream can hang when the body arrives after the headers. Form content
    types leave no raw bytes in the handler, so the parsed form and files count too.
    """
    return bool(
        flask_request.content_length or flask_request.get_data() or flask_request.form or flask_request.files
    )


def require_empty_body():
    """DELETE takes no request body (core §16.1.4)."""
    if request_has_content():
        raise ProblemException(status=400, title="Bad Request", detail="Request body must be empty for DELETE method")


def map_request(mapper, *args):
    """Runs an RPP to model mapper, translating what it rejects."""
    try:
        return mapper(*args)
    except UnsupportedRppFeature as e:
        raise ProblemException(
            status=http_status(e.code), title=e.code.value[1], detail=str(e), headers=problem_headers(e.code),
        )
    except ValidationError as e:
        # Only the message: str(e) would print the request, including its authInfo.
        raise ProblemException(status=400, title="Bad Request", detail=e.message)
    except Exception as e:
        raise ProblemException(status=400, title="Bad Request", detail=str(e))


def rpp_operation(handler):
    """Answers anything a handler did not expect with a Problem Detail."""
    @functools.wraps(handler)
    def wrapper(*args, **kwargs):
        try:
            return handler(*args, **kwargs)
        except ProblemException:
            raise
        except Exception as e:
            raise ProblemException(status=500, title="Internal Server Error", detail=str(e))
    return wrapper
