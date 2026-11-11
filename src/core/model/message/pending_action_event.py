from dataclasses import dataclass
from typing import Optional


@dataclass(kw_only=True)
class PendingActionEvent:
    """The result of a pending action, reported by a queued message."""
    objectType: str
    objectId: str
    approved: bool
    clientTransactionId: Optional[str]
    serverTransactionId: str
    completionDate: str
