from dataclasses import dataclass, field
from typing import List, Optional

from .common import AuthInfo
from .postal_info_change import PostalInfoChange


@dataclass(kw_only=True)
class ContactUpdateChange:
    """What a contact update changes. `voice` and `fax` "" clear the number."""
    postal_info: List[PostalInfoChange] = field(default_factory=list)
    voice: Optional[str] = None
    fax: Optional[str] = None
    email: Optional[str] = None
    authInfo: Optional[AuthInfo] = None

    def __bool__(self) -> bool:
        return bool(
            self.postal_info or self.voice is not None or self.fax is not None or self.email or self.authInfo
        )
