"""The extensions a backend holds are listed in its own package (`registry_adapter.<backend>.extensions.PARTS`, #267), as
plain strings, so that importing the catalogue imports no extension. The strings cannot be checked by import there, so
these tests check them against the extensions."""
import dataclasses
import importlib
import subprocess
import sys

import pytest

from registry_adapter.rri.extensions import PARTS as RRI_PARTS
from registry_adapter.sqlite.extensions import PARTS as SQLITE_PARTS
from registry_setup import backend_parts, held_parts, load_registry
from registration import load_extensions
from settings.load_settings import load_settings
from tests.helper.test_environment import REPOSITORY

# The extension package of each part module, by the backend's catalogue.
CATALOGUES = {"rri": RRI_PARTS, "sqlite": SQLITE_PARTS}
ENVIRONMENTS = {"rri": ["rri-mtest.yaml", "rri-local.yaml"], "sqlite": ["sqlite-demo.yaml", "sqlite-demo-extended.yaml", "sqlite-demo-bound.yaml", "sqlite-demo-inherit.yaml"]}


def _extension_id(part_module: str, backend: str) -> str:
    """The `EXTENSION_ID` of the extension that a part module of the backend belongs to (same package name)."""
    name = part_module.rsplit(".", 1)[1]
    for core in ("core.extension_id", "core.model.extension_id", "core.ports.%s_gateways" % name):
        try:
            return importlib.import_module(f"extensions.{name}.{core}").EXTENSION_ID
        except (ImportError, AttributeError):
            continue
    raise AssertionError(f"no EXTENSION_ID found for extension {name}")


@pytest.mark.parametrize("backend", CATALOGUES)
def test_every_key_of_a_catalogue_is_the_id_of_the_extension_its_part_belongs_to(backend):
    for extension_id, part_module in CATALOGUES[backend].items():
        assert extension_id == _extension_id(part_module, backend)
        assert importlib.import_module(part_module)


@pytest.mark.parametrize("backend", CATALOGUES)
def test_every_extension_of_the_configurations_of_a_backend_is_in_its_catalogue(backend):
    for name in ENVIRONMENTS[backend]:
        path = REPOSITORY / "config" / "environments" / name
        settings = load_settings(str(path))
        registry = load_extensions(settings.extensions)
        assert set(registry.ids()) <= set(CATALOGUES[backend]), name


def test_the_parts_of_a_backend_are_those_of_the_registered_extensions_only():
    settings = load_settings(str(REPOSITORY / "config/environments/sqlite-demo.yaml"))
    registry = load_registry(dataclasses.replace(settings, extensions=("extensions.planets",)))

    assert backend_parts("sqlite", registry) == {"org.example.rpp.extension.planets": SQLITE_PARTS["org.example.rpp.extension.planets"]}


def test_an_extension_the_rri_backend_does_not_list_stops_the_app():
    settings = load_settings(str(REPOSITORY / "config/environments/rri-local.yaml"))

    with pytest.raises(ValueError, match="has no part in the rri backend"):
        load_registry(dataclasses.replace(settings, extensions=("extensions.planets",)))


def test_a_backend_without_an_extensions_package_holds_none():
    assert held_parts("epp") == {}


def test_importing_a_catalogue_imports_no_extension():
    script = (f"import sys; sys.path.insert(0, {str(REPOSITORY / 'src')!r}); import registry_adapter.rri.extensions, registry_adapter.sqlite.extensions; "
              "print([m for m in sys.modules if m.startswith('extensions')])")
    result = subprocess.run([sys.executable, "-I", "-c", script], capture_output=True, text=True, check=True)

    assert result.stdout.strip() == "[]"
