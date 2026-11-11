from dataclasses import dataclass
from typing import Optional

from core.model.domain.domains import Domain
from core.result.operation_response import OperationResponse


@dataclass(kw_only=True)
class DomainMutationResult:
    """A mutation the registry applied. `domain` is None when it could not be read back."""
    mutation: OperationResponse
    domain: Optional[Domain] = None
