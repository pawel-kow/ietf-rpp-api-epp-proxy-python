from registry_adapter.sqlite.extensions import PARTS
from registration import ExtensionRegistry, RegisteredExtension


def register_definitions(registry: ExtensionRegistry, name: str, presets=(), profiles=()) -> None:
    """Registers an extension that brings only presets and profiles (`(identifier, definition)` pairs of
    `tests/helper/preset_fixtures.py`): no data object and no path, and a SQLite part without tables (the backend holds only extensions that have a part)."""
    identifier = f"org.example.rpp.extension.{name}"
    # The SQLite backend holds what its catalogue lists: this extension is test-only, so its entry is made here, in the
    # process that registers it (a test that starts the server in a process of its own too), never in production code; `tests/conftest.py` restores the catalogue after each test.
    PARTS.setdefault(identifier, "tests.refused_configs.definitions_sqlite_part")
    registry.add(RegisteredExtension(
        id=identifier,
        schema={"$id": f"https://example.org/{name}", "rpp:extension": {"id": identifier, "name": name, "version": "1.0"},
                "rpp:extends": {}, "$defs": {}},
        data_objects={}, objects=(),
        presets={key.rsplit(".", 1)[1]: data for key, data in presets},
        profiles={key.rsplit(".", 1)[1]: data for key, data in profiles}))
