import json
from pathlib import Path

from extensions.planets.core.ports.planets_gateways import EXTENSION_ID
from extensions.planets.rpp.schema.openapi_fragment import HANDLERS, openapi_fragment
from extensions.planets.rpp.schema.definition_builders import preset, preset_id, profile, profile_id
from registration import ExtensionRegistry, RegisteredExtension

SCHEMA = Path(__file__).parent / "rpp" / "schema" / "planets-extension.schema.json"

# The top-level data elements of the objects, with their Visibility (docs/demo/planets-extension.md).
DATA_OBJECTS = {
    "planet": {"id": "default", "provMetadata": "default", "type": "default", "radius": "default", "mass": "default",
               "authInfo": "default", "satellite": "onDemand", "processes": "default"},
    "satellite": {"id": "default", "provMetadata": "default", "planet": "default", "orbitalPeriod": "default"},
}

TRANSFER_OPERATIONS = ["request", "query", "cancel", "approve", "reject"]

PRESET_KEY = "planets"

BASE_PRESET = "urn:ietf:params:rpp:preset:base"

SCHEMAS = Path(__file__).parent / "rpp" / "schema"

# The profiles of the extension (docs/demo/<key>-profile.md) and the presets that offer it: the extension alone, and with the
# profiles that constrain it. The presets that add other extensions are brought by those extensions.
PROFILES = {
    "rocky-planets": profile(
        "rocky-planets", "Rocky planets profile", "Constrains the type of a planet to rocky.",
        SCHEMAS / "rocky-planets-profile.schema.json", required=[EXTENSION_ID]),
    "catalogued-satellites": profile(
        "catalogued-satellites", "Catalogued satellites profile",
        "Constrains the identifier of a satellite to a catalogue designation, a name and a roman numeral.",
        SCHEMAS / "catalogued-satellites-profile.schema.json", required=[EXTENSION_ID]),
}

PRESETS = {
    PRESET_KEY: preset(PRESET_KEY, "Planets preset", "The planets and satellites of the SQLite backend, with no constraint.",
                       base_presets=[BASE_PRESET], extensions=[EXTENSION_ID]),
    "catalogued-planets": preset(
        "catalogued-planets", "Catalogued planets preset", "The planets preset, constrained to rocky planets and catalogued satellites.",
        base_presets=[preset_id(PRESET_KEY)], profiles=[profile_id("rocky-planets"), profile_id("catalogued-satellites")]),
}


def register(registry: ExtensionRegistry) -> None:
    """Registers every part of the extension in the pipeline: its schema, the data model, the OpenAPI fragment and the
    handlers of its paths, its objects, its part of the SQLite backend, the leaves it adds to the backend profile, and the
    RPP preset that offers it."""
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads(SCHEMA.read_text(encoding="utf-8")),
        data_objects=DATA_OBJECTS,
        objects=("planet", "satellite"),
        openapi=openapi_fragment,
        handlers=HANDLERS,
        profile_layer={
            "objects": ["planet", "satellite"],
            "extensions": [EXTENSION_ID],
            "planet": {"processes": {"transfer": {"operations": TRANSFER_OPERATIONS}}},
        },
        profile_leaves={"planet.processes.transfer.operations": tuple},
        presets=PRESETS,
        profiles=PROFILES,
    ))
