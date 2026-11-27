"""The message types extensions define (`MESSAGE_MAPPERS`): how the event of an extension, which the core model of a message holds
(`ExtensionEvent`), becomes the `data` of a message. An extension registers its mapper in its `register` function, once
(a second registration of the same id is no change, as for the schemas of the extensions)."""
from typing import Protocol


class MessageMapper(Protocol):
    extension_id: str

    def to_rpp(self, event) -> dict:
        """The `data` of the message (with its `@type`, one of the message types the extension maps with `rpp:messages`)."""


class MessageMappers:
    def __init__(self):
        self._by_id: dict[str, MessageMapper] = {}

    def add(self, mapper: MessageMapper) -> None:
        self._by_id.setdefault(mapper.extension_id, mapper)

    def of(self, extension_id: str) -> MessageMapper | None:
        return self._by_id.get(extension_id)


MESSAGE_MAPPERS = MessageMappers()
