import logging
import re

from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from core.result.unknown_result_code import UnknownResultCode
from registry_adapter.common.xmlsafe.xml_helper import decode_xml
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response, map_epp_code

logger = logging.getLogger("uvicorn.error")

EPP_NS = {"epp": "urn:ietf:params:xml:ns:epp-1.0"}

UNREADABLE = "The reply of the EPP server cannot be read, so the message cannot be acknowledged"


def result_code_of(code: str) -> ResultCode | UnknownResultCode:
    """The code of a reply. One the proxy has no name for is carried as it is (core §18.1, Table 10)."""
    try:
        return map_epp_code(code)
    except KeyError:
        logger.warning("The EPP server sent the result code %s, which the proxy does not know", code)
        return UnknownResultCode(value=(code, "Result code not known to the proxy"))


def decode(xml_string: str):
    """The reply as markup, or None when it is not even that."""
    try:
        return decode_xml(xml_string)
    except Exception:
        return None


def raw_header(root, client_transaction_id) -> dict | None:
    """The header of a reply read as markup, or None when it has no result code."""
    result = root.find("./epp:response/epp:result", EPP_NS) if root is not None else None
    if result is None or not re.fullmatch(r"[0-9]{4}", result.get("code") or ""):
        return None
    msg = result.find("epp:msg", EPP_NS)
    sv_trid = root.find("./epp:response/epp:trID/epp:svTRID", EPP_NS)
    return {
        "code": result_code_of(result.get("code")),
        "msg": (msg.text or "") if msg is not None else "",
        "server_transaction_id": sv_trid.text if sv_trid is not None else None,
        "client_transaction_id": client_transaction_id,
    }


def count_of(msg_q) -> int | None:
    try:
        return int(msg_q.get("count"))
    except (TypeError, ValueError):
        return None


def unreadable(header, client_transaction_id) -> ErrorResponse:
    """A reply the proxy cannot act on: 1301 promises a message to acknowledge, and one without its id is not
    an empty queue. A reply without a result code is no reply."""
    logger.warning("The EPP server sent a reply without a message id or result code, which cannot be used")
    return ErrorResponse(
        code=ResultCode.COMMAND_FAILED, msg=UNREADABLE,
        server_transaction_id=header["server_transaction_id"] if header else None,
        client_transaction_id=header["client_transaction_id"] if header else client_transaction_id,
    )


def parse_error_response(xml_string: str, client_transaction_id: str | None) -> ErrorResponse:
    """The EPP error of a command. A code the proxy has no name for keeps its number, msg and svTRID."""
    try:
        return get_epp_error_response(xml_string, client_transaction_id=client_transaction_id)
    except Exception as e:
        logger.warning("The EPP error reply cannot be read as typed data: %s", type(e).__name__)
    header = raw_header(decode(xml_string), client_transaction_id)
    if header is None:
        return ErrorResponse(
            code=ResultCode.COMMAND_FAILED, msg="The reply of the EPP server cannot be read",
            server_transaction_id=None, client_transaction_id=client_transaction_id,
        )
    return ErrorResponse(**header)
