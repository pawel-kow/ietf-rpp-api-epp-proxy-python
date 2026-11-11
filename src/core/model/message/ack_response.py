from dataclasses import dataclass
from typing import Optional

from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class AckResponse(OperationResponse):
    queue_size: Optional[int]
