"""The message types of the registry changes extension (docs/extensions/registry-changes-extension.md): the events of its core as
the `data` of a message, for the definitions `rpp:messages` of its schema maps."""
from extensions.messages.rpp.mapping.components import notice, reference, subject
from extensions.registry_changes.core.extension_id import EXTENSION_ID
from extensions.registry_changes.core.model.contact_deletion_event import ContactDeletionEvent
from extensions.registry_changes.core.model.registry_change_event import RegistryChangeEvent


class RegistryChangesMessageMapper:
    """Maps the events of the registry changes extension to the data of its message types."""
    extension_id = EXTENSION_ID

    def to_rpp(self, event) -> dict:
        if isinstance(event, RegistryChangeEvent):
            return {"@type": event.kind.value, **subject(event.object), "notices": [notice(n) for n in event.notices]}
        if isinstance(event, ContactDeletionEvent):
            return {"@type": "contactDeletionMessage", "objects": [reference(r) for r in event.objects]}
        raise ValueError(f"No message type of the registry changes extension for {type(event).__name__}")
