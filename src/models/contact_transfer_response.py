from dataclasses import dataclass
from typing import Optional

from .contact_transfer_process import ContactTransferProcess
from .response import OperationResponse


@dataclass(kw_only=True)
class ContactTransferResponse(OperationResponse):
    transfer: Optional[ContactTransferProcess]
