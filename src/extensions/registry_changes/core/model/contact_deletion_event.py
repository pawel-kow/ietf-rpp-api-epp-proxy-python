from dataclasses import dataclass

from extensions.messages.core.model.object_reference import ObjectReference


@dataclass(kw_only=True)
class ContactDeletionEvent:
    """The registry deleted contacts that no domain name referred to."""
    objects: tuple[ObjectReference, ...]
