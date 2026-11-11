import logging
import re
import uuid

from connexion import request

from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode

logger = logging.getLogger("uvicorn.error")

PRINTABLE_ASCII = re.compile(r"[\x20-\x7e]+")
RPP_MEDIA_TYPE = "application/rpp+json"


def client_transaction_id() -> str | None:
    return request.headers.get("RPP-Cltrid")


def rpp_code(code: ResultCode) -> str:
    """The RPP result code of an EPP code: EPP-derived codes have a leading 0 (core §18)."""
    return f"0{code.value[0]}"


def server_transaction_id_of(value: str | None) -> str:
    """RPP-Svtrid: the id of the EPP reply, when a header can carry it, otherwise a new one.

    The id comes from the backend, and a value with other than printable ASCII cannot be a header value.
    """
    stripped = (value or "").strip()  # a header value cannot start or end with a space
    if stripped and PRINTABLE_ASCII.fullmatch(stripped):
        return stripped
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
