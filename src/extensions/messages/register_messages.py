import json
from pathlib import Path

from extensions.messages.core.extension_id import EXTENSION_ID
from registration import ExtensionRegistry, RegisteredExtension


SCHEMAS = Path(__file__).parent / "rpp" / "schema"


def register(registry: ExtensionRegistry) -> None:
    """Registers the extension (docs/extensions/messages-extension.md): its schema, its part of the RRI backend, and the extension in the
    backend profile. It has no object and no message type: the Component Objects of the message types of other extensions."""
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads((SCHEMAS / "messages-extension.schema.json").read_text(encoding="utf-8")),
        data_objects={},
        objects=(),
        backend_parts={"rri": "registry_adapter.rri.extensions.messages"},
        profile_layer={"extensions": [EXTENSION_ID]},
    ))
