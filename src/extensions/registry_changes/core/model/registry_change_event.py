from dataclasses import dataclass

from extensions.messages.core.model.object_reference import ObjectReference
from extensions.messages.core.model.registry_notice import RegistryNotice
from extensions.registry_changes.core.model.registry_change_kind import RegistryChangeKind


@dataclass(kw_only=True)
class RegistryChangeEvent:
    """The registry changed or deleted one object, with its notices."""
    kind: RegistryChangeKind
    object: ObjectReference
    notices: tuple[RegistryNotice, ...]
