"""Runs one RRI request and turns its reply into an `OperationResponse` or an `ErrorResponse`."""
import logging
import re
import uuid
from typing import Callable

from core.result.error_response import ErrorResponse
from core.result.operation_response import OperationResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.result_codes import result_code
from registry_adapter.rri.xml.generated.global_5_0 import RegistryRequest
from registry_adapter.rri.xml.generated.transaction_5_0 import LevelType, ResultType, TransactionType

logger = logging.getLogger(__name__)

# tr:idType is a token of 3 to 64 characters: no leading, trailing or double space, no other whitespace. 60 leave room
# for the suffix `-n` that marks the further commands of one request (gap Q18).
TOKEN = re.compile(r"[^\s]+(?: [^\s]+)*")
MAX_CLIENT_CTID = 60


def _is_token(value: str) -> bool:
    return 3 <= len(value) <= MAX_CLIENT_CTID and TOKEN.fullmatch(value) is not None


def ctid(client_transaction_id: str | None, n: int = 1) -> str:
    """The CTID of the n-th write of a request: the client's id, `-n` added for the further ones, so the registry's
    records name it. A client id that is no token of the allowed length gives a new one. RRI refuses a CTID used
    before (63000060504), as EPP servers refuse a used clTRID."""
    if client_transaction_id and _is_token(client_transaction_id):
        return client_transaction_id if n == 1 else f"{client_transaction_id}-{n}"
    return str(uuid.uuid4())


def data_of(transaction: TransactionType, *types):
    """The first element of the reply's data of one of the types, None when there is none."""
    if transaction.data is None:
        return None
    for item in transaction.data.other_element:
        if isinstance(item, types):
            return item
    return None


def _log_messages(transaction: TransactionType):
    """Warnings and errors of a reply are logged with their codes only: their texts and arguments can hold personal
    data (docs/agents/security.project.md)."""
    codes = [f"{m.level.value}:{m.code}" for m in transaction.message if m.level != LevelType.INFO]
    if codes:
        logger.warning("RRI %s with messages %s", transaction.result.value, ", ".join(codes))


def first_error(transaction: TransactionType):
    for message in transaction.message:
        if message.level == LevelType.ERROR:
            return message
    return None


def run(client, client_transaction_id, *, write: bool, n: int = 1, payload_of: Callable | None = None,
        codes: dict | None = None, **command) -> OperationResponse | ErrorResponse:
    """Sends the command (one keyword: the field of `RegistryRequest` and its value). A write carries a CTID. The
    answer echoes the client's transaction id, as every answer of the proxy does. `codes` maps the DENIC codes whose
    meaning depends on the command, ahead of the general table."""
    request = RegistryRequest(**command, ctid=ctid(client_transaction_id, n) if write else None)
    transaction = client.send(request).transaction
    _log_messages(transaction)
    if transaction.result == ResultType.SUCCESS:
        return OperationResponse(
            code=ResultCode.COMMAND_COMPLETED_SUCCESSFULLY, msg="Command completed successfully",
            server_transaction_id=transaction.stid, client_transaction_id=client_transaction_id,
            payload=payload_of(transaction) if payload_of else None,
        )
    error = first_error(transaction)
    denic_code = str(error.code) if error is not None and error.code is not None else None
    return ErrorResponse(
        code=(codes or {}).get(denic_code) or result_code(denic_code), msg=(error.text if error is not None and error.text else transaction.result.value),
        server_transaction_id=transaction.stid, client_transaction_id=client_transaction_id,
        registry_code=denic_code,
    )


def refused(code: ResultCode, msg: str, client_transaction_id) -> ErrorResponse:
    """A refusal of the adapter, before any command."""
    return ErrorResponse(code=code, msg=msg, server_transaction_id=None, client_transaction_id=client_transaction_id)
