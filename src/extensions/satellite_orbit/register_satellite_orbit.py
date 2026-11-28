import json
from pathlib import Path

from extensions.planets.rpp.mapping.object_members import SATELLITE_MEMBERS
from extensions.planets.rpp.schema.definition_builders import preset, preset_id
from extensions.satellite_orbit.core.model.extension_id import EXTENSION_ID
from extensions.satellite_orbit.rpp.mapping.orbit_mapper import OrbitMapper
from registration import ExtensionRegistry, RegisteredExtension

SCHEMA = Path(__file__).parent / "rpp" / "schema" / "satellite-orbit-extension.schema.json"

# The presets that offer the extension (docs/demo/<key>-preset.md). `planets-complete` builds on the preset of the atmosphere
# extension, so a configuration that offers it registers that extension too.
PRESETS = {
    "planets-orbits": preset(
        "planets-orbits", "Planets with orbits preset", "The planets preset with the orbit of a satellite.",
        base_presets=[preset_id("planets")], extensions=[EXTENSION_ID]),
    "planets-complete": preset(
        "planets-complete", "Complete planets preset", "Builds on the planets with atmospheres and the planets with orbits presets.",
        base_presets=[preset_id("planets-atmosphere"), preset_id("planets-orbits")]),
}


def register(registry: ExtensionRegistry) -> None:
    """Registers the extension in the pipeline: its schema, its mapper for the members of a satellite, its part of the SQLite
    backend (the table and the hook), the extension it adds to the backend profile, and its presets. It needs the planets
    extension, which defines what it adds to."""
    SATELLITE_MEMBERS.add(OrbitMapper())
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads(SCHEMA.read_text(encoding="utf-8")),
        data_objects={},
        objects=(),
        profile_layer={"extensions": [EXTENSION_ID]},
        presets=PRESETS,
    ))
