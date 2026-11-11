from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(kw_only=True)
class ContactUpdateChanges:
    """The statuses a contact update adds or removes."""
    status: List[str] = field(default_factory=list)
    status_reasons: Dict[str, str] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return bool(self.status)
