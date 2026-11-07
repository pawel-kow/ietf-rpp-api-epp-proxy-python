from dataclasses import dataclass
from typing import Optional

from .domain_transfer_process import DomainTransferProcess
from .response import OperationResponse


@dataclass(kw_only=True)
class DomainTransferResponse(OperationResponse):
    transfer: Optional[DomainTransferProcess]
