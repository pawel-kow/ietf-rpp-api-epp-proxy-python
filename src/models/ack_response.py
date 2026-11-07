from dataclasses import dataclass
from typing import Optional

from .response import OperationResponse


@dataclass(kw_only=True)
class AckResponse(OperationResponse):
    queue_size: Optional[int]
