"""The extensions the SQLite backend holds: the module of its part of each, by extension id (the `EXTENSION_ID` of the
extension). Plain strings, so that importing this imports no extension, and a deployment loads only the parts of the
extensions it configures. An extension of `rpp_extensions` that is not here stops the app at start."""

PARTS = {
    "org.example.rpp.extension.planets": "registry_adapter.sqlite.extensions.planets",
    "org.example.rpp.extension.planet-atmosphere": "registry_adapter.sqlite.extensions.planet_atmosphere",
    "org.example.rpp.extension.satellite-orbit": "registry_adapter.sqlite.extensions.satellite_orbit",
}
