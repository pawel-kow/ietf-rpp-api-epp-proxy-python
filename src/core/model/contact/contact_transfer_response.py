from dataclasses import dataclass
from typing import Optional

from core.model.shared.contact_transfer_process import ContactTransferProcess
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class ContactTransferResponse(OperationResponse):
    transfer: Optional[ContactTransferProcess]
