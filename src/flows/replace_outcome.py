from dataclasses import dataclass
from typing import Any, Optional

from models import OperationResponse


@dataclass(kw_only=True)
class ReplaceOutcome:
    """A full update. `current` is the read it was derived from. Without an `update` nothing changed, and nothing was
    sent. Otherwise `mutation` is the registry's answer to the update."""
    current: OperationResponse
    update: Optional[Any] = None
    mutation: Optional[OperationResponse] = None

    @property
    def unchanged(self) -> bool:
        return self.update is None
