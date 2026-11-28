from dataclasses import dataclass
from typing import Optional

from extensions.rri.core.model.object_reference import ObjectReference
from extensions.rri.core.model.registry_notice import RegistryNotice


@dataclass(kw_only=True)
class DomainStatusMessageEvent:
    """The status the registry decided for a domain name after a request, with the holders it concerns and the deadlines to provide
    verification information."""
    object: ObjectReference
    status: tuple[str, ...]
    holders: tuple[ObjectReference, ...]
    hold_deadline: Optional[str] = None
    deletion_deadline: Optional[str] = None
    notices: tuple[RegistryNotice, ...] = ()
