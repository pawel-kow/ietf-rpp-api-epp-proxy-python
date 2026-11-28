import json
from pathlib import Path

from extensions.registry_changes.core.extension_id import EXTENSION_ID
from extensions.registry_changes.rpp.mapping.messages import RegistryChangesMessageMapper
from registration import ExtensionRegistry, RegisteredExtension
from rpp.mapping.message.message_mappers import MESSAGE_MAPPERS

SCHEMAS = Path(__file__).parent / "rpp" / "schema"


def register(registry: ExtensionRegistry) -> None:
    """Registers the extension (docs/extensions/registry-changes-extension.md): its schema, the mapper of its message types, its part of
    the RRI backend, and the extension in the backend profile. It has no object. It depends on the messages extension."""
    MESSAGE_MAPPERS.add(RegistryChangesMessageMapper())
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads((SCHEMAS / "registry-changes-extension.schema.json").read_text(encoding="utf-8")),
        data_objects={},
        objects=(),
        backend_parts={"rri": "registry_adapter.rri.extensions.registry_changes"},
        profile_layer={"extensions": [EXTENSION_ID]},
    ))
