from dataclasses import dataclass
from typing import Optional

from extensions.rri.core.model.object_reference import ObjectReference
from extensions.rri.core.model.registry_notice import RegistryNotice


@dataclass(kw_only=True)
class ContactVerificationMessageEvent:
    """A contact whose claims must be verified, and the domain names that the registry places on hold or deletes first."""
    object: ObjectReference
    claims: tuple[str, ...]
    referenced_domains: int
    earliest_hold: Optional[ObjectReference]
    earliest_deletion: ObjectReference
    notices: tuple[RegistryNotice, ...] = ()
