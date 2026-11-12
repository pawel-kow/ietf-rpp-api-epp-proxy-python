from dataclasses import dataclass
from typing import Optional

from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class ErrorResponse(OperationResponse):
    """A refusal. `registry_code` is the backend's own code of the refusal where it has a finer one than `code`, which
    the detail of the answer names."""
    registry_code: Optional[str] = None
