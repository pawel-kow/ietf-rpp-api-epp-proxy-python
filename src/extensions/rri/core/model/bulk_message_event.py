from dataclasses import dataclass

from extensions.rri.core.model.message_kind import RriMessageKind
from extensions.messages.core.model.object_reference import ObjectReference


@dataclass(kw_only=True)
class BulkMessageEvent:
    """A notification about several objects: domain names that expire (with their dates)."""
    kind: RriMessageKind
    objects: tuple[ObjectReference, ...]
