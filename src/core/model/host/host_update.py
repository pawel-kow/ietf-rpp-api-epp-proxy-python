from dataclasses import dataclass
from typing import Optional

from core.model.host.host_update_changes import HostUpdateChanges


@dataclass(kw_only=True)
class HostUpdate:
    name: str
    new_name: Optional[str] = None
    add: Optional[HostUpdateChanges] = None
    remove: Optional[HostUpdateChanges] = None
