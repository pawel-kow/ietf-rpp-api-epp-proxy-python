"""The notifications of the registry (QUEUE-READ) that the registry changes extension has a message type for: `domainUpdate`,
`contactUpdate`, `domainDelete` and `contactDelete`, as the events of the extension's core
(docs/extensions/registry-changes-extension.md)."""
from core.model.message.extension_event import ExtensionEvent
from extensions.registry_changes.core.extension_id import EXTENSION_ID
from extensions.registry_changes.core.model.contact_deletion_event import ContactDeletionEvent
from extensions.registry_changes.core.model.registry_change_event import RegistryChangeEvent
from extensions.registry_changes.core.model.registry_change_kind import RegistryChangeKind
from registry_adapter.rri.extensions.messages.references import contact_reference, domain_reference, registry_notices
from registry_adapter.rri.message_type import RriMessageType
from registry_adapter.rri.xml.generated.message_5_0 import Message, MsgTypeType


def _domain_change(kind: RegistryChangeKind, attribute: str):
    def translate(message: Message):
        element = getattr(message, attribute)
        return ExtensionEvent(extension_id=EXTENSION_ID, event=RegistryChangeEvent(
            kind=kind, object=domain_reference(element.domain), notices=registry_notices(element.message)))
    return translate


def _contact_update(message: Message):
    element = message.contact_update
    return ExtensionEvent(extension_id=EXTENSION_ID, event=RegistryChangeEvent(
        kind=RegistryChangeKind.CONTACT_UPDATED, object=contact_reference(element.contact.handle),
        notices=registry_notices(element.message)))


def _contact_deletion(message: Message):
    return ExtensionEvent(extension_id=EXTENSION_ID, event=ContactDeletionEvent(
        objects=tuple(contact_reference(handle) for handle in message.contact_delete.handles.handle)))


MESSAGE_TYPES = (
    RriMessageType(msg_type=MsgTypeType.DOMAIN_UPDATE, identifier=RegistryChangeKind.DOMAIN_UPDATED.value,
                   translate=_domain_change(RegistryChangeKind.DOMAIN_UPDATED, "domain_update")),
    RriMessageType(msg_type=MsgTypeType.CONTACT_UPDATE, identifier=RegistryChangeKind.CONTACT_UPDATED.value,
                   translate=_contact_update),
    RriMessageType(msg_type=MsgTypeType.DOMAIN_DELETE, identifier=RegistryChangeKind.DOMAIN_DELETED.value,
                   translate=_domain_change(RegistryChangeKind.DOMAIN_DELETED, "domain_delete")),
    RriMessageType(msg_type=MsgTypeType.CONTACT_DELETE, identifier="contactDeletionMessage", translate=_contact_deletion),
)
