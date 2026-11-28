"""An app built without an extension does not know it: no path, no operationId of its handlers, no module loaded, no
leaf. An extension the configuration names that cannot start stops the app."""
import dataclasses
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest
from starlette.testclient import TestClient

from main import compose
from rpp.schema.extension_registration import check_names
from rpp.schema.extensions import register_extension
from settings.load_settings import load_settings
from tests.helper.test_environment import REPOSITORY

DEMO = str(REPOSITORY / "config/environments/sqlite-demo.yaml")


def demo_settings(**changes):
    return dataclasses.replace(load_settings(DEMO), **changes)


def spec_of(composition) -> dict:
    return TestClient(composition.app).get("/openapi.json").json()


def test_an_app_without_the_extension_has_no_planet_path_and_no_handler_of_it():
    composition = compose(demo_settings(extensions=(), profile_layers=_layers_without_extension()))
    try:
        paths = spec_of(composition)["paths"]
        profile = composition.profile
    finally:
        composition.sessions.close()

    assert not [path for path in paths if path.startswith(("/planets", "/satellites"))]
    operation_ids = [operation["operationId"] for item in paths.values() for operation in item.values()]
    assert not [operation_id for operation_id in operation_ids if operation_id.startswith("extensions.")]
    assert profile.objects == ("message",) and profile.extensions == ()
    with pytest.raises(AttributeError):
        profile.planet


def test_an_app_with_the_extension_has_its_paths_and_handlers():
    composition = compose(demo_settings())
    try:
        paths = spec_of(composition)["paths"]
    finally:
        composition.sessions.close()

    assert {"/planets", "/planets/{id}", "/planets/{id}/satellites/{satelliteId}", "/satellites/{id}/availability",
            "/planets/{id}/processes/transferProcesses/latest/transferApprove"} <= set(paths)


def _layers_without_extension():
    generic, specific = demo_settings().profile_layers
    return generic, {"presets": ["base"], "default_preset": "base"}


def test_the_generic_code_loads_nothing_of_an_extension_unless_configured():
    """In a process of its own, as another test of this one's process may have registered it."""
    script = textwrap.dedent(f"""
        import os, sys
        sys.path.insert(0, {str(REPOSITORY / 'src')!r})
        os.environ["RPP_CONFIG_FILE"] = {str(REPOSITORY / 'config' / 'environments' / 'epp-docker.yaml')!r}
        import main
        from rpp.schema.extensions import EXTENSIONS
        loaded = sorted(name for name in sys.modules if name == "extensions" or name.startswith("extensions."))
        loaded += sorted(name for name in sys.modules if "planets" in name)
        print(loaded, [e for e in EXTENSIONS if "planets" in e], [])
    """)

    result = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, check=True)

    assert result.stdout.strip().splitlines()[-1] == "[] [] []"


def test_a_configured_extension_that_does_not_exist_stops_the_app():
    with pytest.raises(ValueError, match="cannot import 'extensions.nowhere'"):
        compose(demo_settings(extensions=("extensions.nowhere",)))


def test_an_extension_the_backend_cannot_hold_stops_the_app():
    epp = load_settings(str(REPOSITORY / "config/environments/epp-docker.yaml"))

    with pytest.raises(ValueError, match="has no part in the epp backend"):
        compose(dataclasses.replace(epp, extensions=("extensions.planets",)))


SCHEMA = json.loads((Path(__file__).parents[2] / ".spec" / "planets-extension.schema.json").read_text())


def _schema(extension_id, defs):
    return {"$id": "https://x.example/s.json", "rpp:extension": {"id": extension_id, "name": "x", "version": "1.0"},
            "rpp:extends": {}, "$defs": defs}


def test_a_definition_named_as_a_base_definition_is_refused():
    with pytest.raises(ValueError, match="a definition of the base schema"):
        check_names(_schema("x.clash", {"contact.create": {"type": "object"}}))


def test_a_definition_named_as_another_extensions_is_refused():
    register_extension(SCHEMA)

    with pytest.raises(ValueError, match="which the extension org.example.rpp.extension.planets defines"):
        check_names(_schema("x.clash", {"planet.create": {"type": "object"}}))


def test_a_fresh_definition_is_taken():
    check_names(_schema("x.fresh", {"gadget.create": {"type": "object"}}))
