import json
from pathlib import Path

import yaml

from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from extensions.rri.rpp.mapping.request_contact_members import RequestContactMembers
from extensions.rri.rpp.schema.openapi_fragment import HANDLERS, openapi_fragment
from registration import ExtensionRegistry, RegisteredExtension
from rpp.mapping.domain.domain_members import DOMAIN_MEMBERS

SCHEMAS = Path(__file__).parent / "rpp" / "schema"

# The top-level data elements of the objects, with their Visibility (docs/rri/rri-extension.md): a request contact has none
# with onDemand Visibility.
DATA_OBJECTS = {
    "requestContact": {"id": "default", "provMetadata": "default", "uriTemplate": "default"},
}

PRESET_KEY = "rri"

# The request contacts of a domain, 0 to 1 of each role (rri 5.0 reference §5.2): a domain needs none.
REQUEST_CONTACT_LIMITS = {"min_count": 0, "max_count": 1}


def _preset() -> dict:
    """The preset of DENIC's RRI (docs/rri/rri-extension.md): the extension on top of the base preset."""
    return yaml.safe_load((SCHEMAS / "rri-preset.yaml").read_text(encoding="utf-8"))


def register(registry: ExtensionRegistry) -> None:
    """Registers every part of the extension in the pipeline: its schema, the data model, the OpenAPI fragment and the
    handlers of its request contact paths, the mapper of the request contacts of a domain, its part of the RRI backend, the
    leaves it adds to the backend profile, and the RPP preset that offers it."""
    DOMAIN_MEMBERS.add(RequestContactMembers())
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads((SCHEMAS / "rri-extension.schema.json").read_text(encoding="utf-8")),
        data_objects=DATA_OBJECTS,
        objects=("requestContact",),
        openapi=openapi_fragment,
        handlers=HANDLERS,
        backend_parts={"rri": "registry_adapter.rri.extensions.rri"},
        profile_layer={
            "objects": ["requestContact"],
            "extensions": [EXTENSION_ID],
            "presets": [PRESET_KEY],
            "default_preset": PRESET_KEY,
            "domainName": {"generalRequest": REQUEST_CONTACT_LIMITS, "abuse": REQUEST_CONTACT_LIMITS},
        },
        profile_leaves={f"domainName.{role}.{limit}": int for role in ("generalRequest", "abuse")
                        for limit in ("min_count", "max_count")},
        presets={PRESET_KEY: _preset()},
    ))
