from dataclasses import dataclass
from typing import Optional

from core.model.host.host import Host
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class HostMutationResult:
    """A mutation the registry applied. `host` is None when it could not be read back."""
    mutation: OperationResponse
    host: Optional[Host] = None
