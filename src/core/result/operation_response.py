from dataclasses import dataclass
from typing import Optional

from core.result.result_code import ResultCode


@dataclass(kw_only=True)
class OperationResponse:
    code: ResultCode
    msg: str
    server_transaction_id: Optional[str]
    client_transaction_id: Optional[str]
