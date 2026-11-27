"""The registry of the extensions a configuration names (src/registration) and what builds on it."""
import sys
import textwrap

import pytest

from core.capabilities.backend_profile import BackendProfile
from registration import ExtensionRegistry, RegisteredExtension, load_extensions, with_extensions
from tests.helper.profiles import generic_profile


def extension(extension_id="x.ext", **parts):
    return RegisteredExtension(
        id=extension_id, schema={}, data_objects={}, objects=(), openapi=lambda drafts: {"paths": {}}, handlers="x.handlers",
        **parts)


def test_an_extension_is_registered_once():
    registry = ExtensionRegistry()
    registry.add(extension())

    with pytest.raises(ValueError, match="twice"):
        registry.add(extension())
    assert registry.ids() == ("x.ext",)


def test_the_registry_gives_what_each_extension_registered():
    registry = ExtensionRegistry()
    registry.add(extension("a", backend_parts={"sqlite": "mod.a"}, profile_leaves={"a.x": int}))
    registry.add(extension("b", backend_parts={"epp": "mod.b"}, profile_leaves={"b.y": str}))

    assert registry.backend_parts("sqlite") == {"a": "mod.a"}
    assert registry.profile_leaves() == {"a.x": int, "b.y": str}
    assert registry.handler_packages() == ("x.handlers", "x.handlers")


def test_a_module_that_cannot_be_imported_stops_the_app():
    with pytest.raises(ValueError, match="cannot import 'no.such.module'"):
        load_extensions(["no.such.module"])


def test_a_module_without_register_stops_the_app():
    with pytest.raises(ValueError, match="has no register"):
        load_extensions(["json"])


def test_a_module_registers_its_parts(tmp_path, monkeypatch):
    (tmp_path / "demo_extension.py").write_text(textwrap.dedent('''
        from registration import RegisteredExtension

        def register(registry):
            registry.add(RegisteredExtension(id="demo", schema={}, data_objects={}, objects=("thing",),
                                             openapi=lambda drafts: {"paths": {}}, handlers="demo.handlers"))
    '''))
    monkeypatch.syspath_prepend(str(tmp_path))
    try:
        registry = load_extensions(["demo_extension"])
    finally:
        sys.modules.pop("demo_extension", None)

    assert registry.ids() == ("demo",)
    assert registry.get("demo").objects == ("thing",)


def test_without_extensions_the_layers_are_the_generic_ones():
    layers = [{"objects": ["a"]}, {"name": "x"}]

    assert with_extensions(layers, ExtensionRegistry()) == layers


def test_extensions_add_their_objects_and_leaves_to_the_generic_profile():
    registry = ExtensionRegistry()
    registry.add(extension("a", profile_layer={"objects": ["thing"], "extensions": ["a"],
                                               "thing": {"size": 3}}, profile_leaves={"thing.size": int}))
    generic = {"objects": ["domainName"], "extensions": []}
    server = {"profiles": ["base"]}

    layers = with_extensions([generic, server], registry)

    assert layers == [{"objects": ["domainName", "thing"], "extensions": ["a"]}, {"thing": {"size": 3}}, server]
    assert generic == {"objects": ["domainName"], "extensions": []}  # the generic layer itself is not changed


def test_a_leaf_of_an_extension_is_known_with_the_extension_only():
    base = {**_tree(generic_profile("sqlite")), "thing": {"size": 3}}

    with pytest.raises(ValueError, match="unknown thing.size"):
        BackendProfile.from_layers(base)
    profile = BackendProfile.from_layers(base, extra_leaves={"thing.size": int})
    assert profile.thing.size == 3
    assert profile.with_changes({"objects": ["thing"]}).thing.size == 3  # the leaves stay known


def test_a_leaf_of_an_extension_has_its_type():
    base = {**_tree(generic_profile("sqlite")), "thing": {"size": "big"}}

    with pytest.raises(ValueError, match="thing.size must be of type int"):
        BackendProfile.from_layers(base, extra_leaves={"thing.size": int})


def _tree(profile: BackendProfile) -> dict:
    return profile._tree
