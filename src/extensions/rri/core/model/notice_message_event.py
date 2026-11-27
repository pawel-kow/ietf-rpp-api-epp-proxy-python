from dataclasses import dataclass

from extensions.rri.core.model.message_kind import RriMessageKind
from extensions.rri.core.model.object_reference import ObjectReference
from extensions.rri.core.model.registry_notice import RegistryNotice


@dataclass(kw_only=True)
class NoticeMessageEvent:
    """A notification about one object that the registry explains with notices (deletion, lock, unlock, update, release,
    withdrawal of authorisation information, update of a contact)."""
    kind: RriMessageKind
    object: ObjectReference
    notices: tuple[RegistryNotice, ...]
