"""The specifications under docs/rri/ of the DENIC RRI profile and the presets rri and rri-strict (#183), against the definitions
the rri extension registers: the Profile Schema shown is the file, every `valid` example passes with and without the profile, and
a `violates` example passes the preset `rri` and is refused by the preset `rri-strict` (step 2); the Preset Overviews are the
definitions."""
import json
import re
from pathlib import Path

import pytest

from rpp.schema.definitions import Definitions
from rpp.schema.extensions import EXTENSIONS
from rpp.schema.offered_presets import OfferedPresets
from rpp.schema.profile_constraint_violation import ProfileConstraintViolation
from rpp.schema.schema_scope import SchemaScope
from tests.helper.profiles import RRI_REGISTRY
from tests.unit.test_demo_docs import examples, table

pytestmark = pytest.mark.lazy_schemas

ROOT = Path(__file__).parents[2]
DOCS = ROOT / "docs" / "rri"
SPEC = ROOT / ".spec"

DEFINITIONS = Definitions.load(RRI_REGISTRY, EXTENSIONS)
PROFILE = DEFINITIONS.profiles["rri"]
EXTENSION_IDS = ("de.denic.rpp.rri",)


def read(name):
    return (DOCS / name).read_text(encoding="utf-8")


def scope(key):
    offered = OfferedPresets.build(DEFINITIONS, [key], key, {}, EXTENSION_IDS).offered[0]
    return SchemaScope(offered.extensions, offered.applicable, offered.required)


def test_the_profile_specification_shows_its_profile_schema_and_its_overview():
    text = read("rri-profile.md")
    shown = json.loads(re.search(r"<!-- profile-schema -->\n```json\n(.*?)```", text, re.DOTALL).group(1))

    assert shown == PROFILE.schema == json.loads((SPEC / "rri-profile.schema.json").read_text(encoding="utf-8"))
    overview = table(text)
    assert (overview["Name"], overview["Version"], overview["RPP version"]) == (PROFILE.name, PROFILE.version, PROFILE.rpp_version)
    assert overview["Identifier"] == f"`{PROFILE.id}`"
    assert overview["Profile Schema `$id`"] == f"<{PROFILE.schema['$id']}>"
    assert overview["Specification"] == f"<{PROFILE.url}>"
    assert overview["Base profiles"] == "None" and not PROFILE.base_profiles
    assert overview["Required extensions"] == ", ".join(f"`{r.id}` {r.version}" for r in PROFILE.required_extensions)


def test_the_schema_in_the_package_is_the_one_of_the_specification():
    copy = ROOT / "src" / "extensions" / "rri" / "rpp" / "schema" / "rri-profile.schema.json"

    assert json.loads(copy.read_text(encoding="utf-8")) == json.loads((SPEC / "rri-profile.schema.json").read_text(encoding="utf-8"))


def test_the_profile_specification_has_a_violating_example_for_each_constrained_definition():
    found = examples(read("rri-profile.md"))
    constrained = {target.split("#/$defs/")[1] for target in PROFILE.schema["rpp:constraints"]}

    assert {name for kind, name, _ in found if kind == "violates"} == constrained
    assert any(kind == "valid" for kind, _, _ in found)


def test_a_valid_example_passes_with_and_without_the_profile_and_a_violating_one_only_without():
    without, with_ = scope("rri"), scope("rri-strict")

    for kind, name, example in examples(read("rri-profile.md")):
        without.validate_request(name, example)
        if kind == "valid":
            with_.validate_request(name, example)
        else:
            with pytest.raises(ProfileConstraintViolation) as refused:
                with_.validate_request(name, example)
            assert refused.value.profile == PROFILE.id


def listed(cell):
    return [] if cell == "None" else re.findall(r"`([^`]+)` (\S+?)(?:,|$)", cell)


@pytest.mark.parametrize("key, document", [("rri", "rri-preset.md"), ("rri-strict", "rri-strict-preset.md")])
def test_a_preset_specification_states_the_definition_the_extension_registers(key, document):
    text = read(document)
    definition = DEFINITIONS.presets[key]
    overview = table(text)

    assert (overview["Name"], overview["Version"], overview["RPP version"]) == (definition.name, definition.version, definition.rpp_version)
    assert overview["Identifier"] == f"`{definition.id}`"
    if key != "rri":  # the preset rri states no url yet, so that its wire form does not change (#183)
        assert overview["Specification"] == f"<{definition.url}>"
    assert listed(overview["Extensions"]) == [(r.id, r.version) for r in definition.extensions]
    assert listed(overview["Profiles"]) == [(r.id, r.version) for r in definition.profiles]
    assert listed(overview["Base presets"]) == [(r.id, r.version) for r in definition.base_presets]
    assert f"RPP-Preset: preset={definition.id};version={definition.version}" in text


def test_the_strict_preset_is_the_rri_preset_with_the_profile():
    offered = OfferedPresets.build(DEFINITIONS, ["rri-strict"], "rri-strict", {}, EXTENSION_IDS).offered[0]

    assert offered.extension_ids == EXTENSION_IDS
    assert [profile.id for profile in offered.applicable] == [PROFILE.id]
    assert not DEFINITIONS.presets["rri"].profiles


def test_the_specifications_are_ascii_and_have_a_changes_history():
    for name in ("rri-profile.md", "rri-preset.md", "rri-strict-preset.md"):
        text = read(name)
        assert text.isascii(), name
        assert "# Changes History" in text, name
