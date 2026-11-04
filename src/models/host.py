from dataclasses import dataclass
from typing import List, Optional

from .common import ProvisioningObject


@dataclass(kw_only=True)
class Host(ProvisioningObject):
    name: str
    ipv4: Optional[List[str]] = None
    ipv6: Optional[List[str]] = None
