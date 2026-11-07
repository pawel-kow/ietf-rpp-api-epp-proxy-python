from dataclasses import dataclass
from typing import Optional

from .response import OperationResponse


@dataclass(kw_only=True)
class ContactCheckResponse(OperationResponse):
    contact_id: str
    available: bool
    reason: Optional[str] = None
