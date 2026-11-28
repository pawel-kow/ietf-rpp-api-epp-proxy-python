"""The message types of the domain lock extension (docs/extensions/domain-lock-extension.md): the event of its core as the `data`
of a message, for the definitions `rpp:messages` of its schema maps."""
from extensions.domain_lock.core.extension_id import EXTENSION_ID
from extensions.domain_lock.core.model.domain_lock_event import DomainLockEvent
from extensions.messages.rpp.mapping.components import notice, subject


class DomainLockMessageMapper:
    """Maps the event of the domain lock extension to the data of its message types."""
    extension_id = EXTENSION_ID

    def to_rpp(self, event) -> dict:
        if not isinstance(event, DomainLockEvent):
            raise ValueError(f"No message type of the domain lock extension for {type(event).__name__}")
        return {"@type": event.kind.value, **subject(event.object), "notices": [notice(n) for n in event.notices]}
