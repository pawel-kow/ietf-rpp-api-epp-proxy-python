from dataclasses import dataclass
from typing import Optional

from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class DomainTransferResponse(OperationResponse):
    transfer: Optional[DomainTransferProcess]
