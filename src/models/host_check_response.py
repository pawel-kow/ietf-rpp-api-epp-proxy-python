from dataclasses import dataclass
from typing import Optional

from .response import OperationResponse


@dataclass(kw_only=True)
class HostCheckResponse(OperationResponse):
    host_name: str
    available: bool
    reason: Optional[str] = None
