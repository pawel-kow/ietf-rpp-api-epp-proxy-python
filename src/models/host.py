from dataclasses import dataclass, field
from typing import Dict, List, Optional

from .common import ProvisioningObject


@dataclass(kw_only=True)
class Host(ProvisioningObject):
    name: str
    ipv4: Optional[List[str]] = None
    ipv6: Optional[List[str]] = None
    status_reasons: Dict[str, str] = field(default_factory=dict)
