import json
from pathlib import Path

from extensions.domain_lock.core.extension_id import EXTENSION_ID
from extensions.domain_lock.rpp.mapping.messages import DomainLockMessageMapper
from registration import ExtensionRegistry, RegisteredExtension
from rpp.mapping.message.message_mappers import MESSAGE_MAPPERS

SCHEMAS = Path(__file__).parent / "rpp" / "schema"


def register(registry: ExtensionRegistry) -> None:
    """Registers the extension (docs/extensions/domain-lock-extension.md): its schema, the mapper of its message types, its part of
    the RRI backend, and the extension in the backend profile. It has no object. It depends on the messages extension."""
    MESSAGE_MAPPERS.add(DomainLockMessageMapper())
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads((SCHEMAS / "domain-lock-extension.schema.json").read_text(encoding="utf-8")),
        data_objects={},
        objects=(),
        profile_layer={"extensions": [EXTENSION_ID]},
    ))
