from dataclasses import dataclass
from typing import Optional

from extensions.rri.core.model.message_kind import RriMessageKind
from extensions.messages.core.model.object_reference import ObjectReference


@dataclass(kw_only=True)
class AuthInfoMessageEvent:
    """The expiry of the authorisation information of a domain name (with the date), or its issue to the holders (without)."""
    kind: RriMessageKind
    object: ObjectReference
    expiry_date: Optional[str] = None
