from dataclasses import dataclass

from extensions.rri.core.model.message_kind import RriMessageKind
from extensions.rri.core.model.object_reference import ObjectReference


@dataclass(kw_only=True)
class BulkMessageEvent:
    """A notification about several objects: domain names that expire (with their dates) or contacts that were deleted."""
    kind: RriMessageKind
    objects: tuple[ObjectReference, ...]
