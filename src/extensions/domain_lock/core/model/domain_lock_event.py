from dataclasses import dataclass

from extensions.domain_lock.core.model.domain_lock_kind import DomainLockKind
from extensions.messages.core.model.object_reference import ObjectReference
from extensions.messages.core.model.registry_notice import RegistryNotice


@dataclass(kw_only=True)
class DomainLockEvent:
    """The registry locked a domain name, or removed the lock, with its notices."""
    kind: DomainLockKind
    object: ObjectReference
    notices: tuple[RegistryNotice, ...]
