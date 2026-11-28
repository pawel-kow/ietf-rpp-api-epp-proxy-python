import json
from pathlib import Path

from extensions.planet_atmosphere.core.model.extension_id import EXTENSION_ID
from extensions.planet_atmosphere.rpp.mapping.atmosphere_mapper import AtmosphereMapper
from extensions.planets.core.ports.planets_gateways import EXTENSION_ID as PLANETS
from extensions.planets.rpp.mapping.object_members import PLANET_MEMBERS
from extensions.planets.rpp.schema.definition_builders import preset, preset_id, profile, profile_id
from registration import ExtensionRegistry, RegisteredExtension

SCHEMAS = Path(__file__).parent / "rpp" / "schema"

# The profiles that need this extension (docs/demo/<key>-profile.md), and the presets that offer it, alone and with the other
# demo definitions. A definition is only read where a configuration offers it.
PROFILES = {
    "habitable-atmospheres": profile(
        "habitable-atmospheres", "Habitable atmospheres profile",
        "Requires an atmosphere on a planet, with a pressure between 0.5 and 2 bar.",
        SCHEMAS / "habitable-atmospheres-profile.schema.json", required=[PLANETS, EXTENSION_ID]),
    "habitable-rocky-planets": profile(
        "habitable-rocky-planets", "Habitable rocky planets profile",
        "Builds on the rocky planets and habitable atmospheres profiles, and requires the radius of a planet.",
        SCHEMAS / "habitable-rocky-planets-profile.schema.json", required=[PLANETS],
        base_profiles=[profile_id("rocky-planets"), profile_id("habitable-atmospheres")]),
}

PRESETS = {
    "planets-atmosphere": preset(
        "planets-atmosphere", "Planets with atmospheres preset", "The planets preset with the atmosphere of a planet.",
        base_presets=[preset_id("planets")], extensions=[EXTENSION_ID]),
    "habitable-worlds": preset(
        "habitable-worlds", "Habitable worlds preset",
        "Builds on the planets with atmospheres and the catalogued planets presets, and applies the habitable rocky planets profile.",
        base_presets=[preset_id("planets-atmosphere"), preset_id("catalogued-planets")],
        profiles=[profile_id("habitable-rocky-planets")]),
}


def register(registry: ExtensionRegistry) -> None:
    """Registers the extension in the pipeline: its schema, its mapper for the members of a planet, its part of the SQLite backend
    (the table and the hook), the extension it adds to the backend profile, and its presets and profiles. It needs the planets
    extension, which defines what it adds to."""
    PLANET_MEMBERS.add(AtmosphereMapper())
    registry.add(RegisteredExtension(
        id=EXTENSION_ID,
        schema=json.loads((SCHEMAS / "planet-atmosphere-extension.schema.json").read_text(encoding="utf-8")),
        data_objects={},
        objects=(),
        profile_layer={"extensions": [EXTENSION_ID]},
        presets=PRESETS,
        profiles=PROFILES,
    ))
