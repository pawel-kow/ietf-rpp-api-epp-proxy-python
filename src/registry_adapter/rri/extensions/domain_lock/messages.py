"""The notifications of the registry (QUEUE-READ) that the domain lock extension has a message type for: `lockCreate` and `lockDelete`,
as the event of the extension's core (docs/extensions/domain-lock-extension.md)."""
from core.model.message.extension_event import ExtensionEvent
from extensions.domain_lock.core.extension_id import EXTENSION_ID
from extensions.domain_lock.core.model.domain_lock_event import DomainLockEvent
from extensions.domain_lock.core.model.domain_lock_kind import DomainLockKind
from registry_adapter.rri.extensions.messages.references import domain_reference, registry_notices
from registry_adapter.rri.message_type import RriMessageType
from registry_adapter.rri.xml.generated.message_5_0 import MsgTypeType


def _lock(kind: DomainLockKind, attribute: str):
    def translate(message):
        element = getattr(message, attribute)
        return ExtensionEvent(extension_id=EXTENSION_ID, event=DomainLockEvent(
            kind=kind, object=domain_reference(element.domain), notices=registry_notices(element.message)))
    return translate


MESSAGE_TYPES = (
    RriMessageType(msg_type=MsgTypeType.LOCK_CREATE, identifier=DomainLockKind.LOCKED.value,
                   translate=_lock(DomainLockKind.LOCKED, "lock_create")),
    RriMessageType(msg_type=MsgTypeType.LOCK_DELETE, identifier=DomainLockKind.UNLOCKED.value,
                   translate=_lock(DomainLockKind.UNLOCKED, "lock_delete")),
)
