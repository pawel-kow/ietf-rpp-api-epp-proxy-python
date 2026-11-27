"""The checks at start (#178 I3): flattening, cycles, versions, required extensions, Profile Schemas and Extension Schemas,
each refusal naming what conflicts. The criteria of #174 for the server that does not start."""
import pytest

from rpp.schema.definitions import Definitions
from rpp.schema.extensions import EXTENSIONS
from rpp.schema.offered_presets import OfferedPresets
from rpp.schema.rpp_extension import RppExtension
from tests.helper.preset_fixtures import (
    ADMIN_ONLY, AT_MOST_ONE, AUTH_REQUIRED, BASE, definitions_with, preset, profile)

RRI = "de.denic.rpp.rri"
BASE_KEY = "base"


def build(definitions, keys, default=None, bound=None, held=()):
    return OfferedPresets.build(definitions, keys, default or keys[0], bound or {}, held)


def key_of(item):
    return item[0].rsplit(".", 1)[1]


def test_the_standard_presets_flatten_with_the_epp_compatibility_profile_in_the_epp_compatible_one():
    presets = build(Definitions.load(), ["base", "epp-compatible"], "epp-compatible")

    base, epp = presets.offered
    assert base.profiles == () and base.extensions == () and base.applicable == ()
    assert [p.id for p in epp.profiles] == ["urn:ietf:params:rpp:profile:epp-compatibility"]
    assert epp.default and not base.default
    assert presets.default is epp


def test_a_preset_is_the_union_of_its_bases_and_what_two_bases_share_counts_once():
    left = preset("left", base_presets=[BASE["id"]], profiles=[ADMIN_ONLY[0]])
    right = preset("right", base_presets=[BASE["id"]], profiles=[ADMIN_ONLY[0], AUTH_REQUIRED[0]])
    both = preset("both", base_presets=[left[0], right[0]])
    definitions = definitions_with([left, right, both], [ADMIN_ONLY, AUTH_REQUIRED])

    offered = build(definitions, ["both"]).offered[0]

    assert [p.id for p in offered.profiles] == [ADMIN_ONLY[0], AUTH_REQUIRED[0]]


def test_the_extensions_of_the_bases_are_in_the_preset_once():
    left = preset("left", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")])
    right = preset("right", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")])
    both = preset("both", base_presets=[left[0], right[0]])

    offered = build(definitions_with([left, right, both]), ["both"], held=(RRI,)).offered[0]

    assert offered.extension_ids == (RRI,)


def test_the_applicable_profiles_are_those_of_the_preset_the_bound_ones_and_the_bases_of_all():
    plain = preset("plain", base_presets=[BASE["id"]], profiles=[AT_MOST_ONE[0]])
    definitions = definitions_with([plain], [ADMIN_ONLY, AT_MOST_ONE, AUTH_REQUIRED])

    offered = build(definitions, ["plain"], bound={"plain": ["auth-required"]}).offered[0]

    assert [p.id for p in offered.profiles] == [AT_MOST_ONE[0]]
    assert [p.id for p in offered.bound_profiles] == [AUTH_REQUIRED[0]]
    assert sorted(p.id for p in offered.applicable) == sorted([ADMIN_ONLY[0], AT_MOST_ONE[0], AUTH_REQUIRED[0]])


def test_a_cycle_of_presets_or_of_profiles_stops_the_server_and_names_the_cycle():
    one = preset("one", base_presets=["org.example.rpp.preset.two"])
    two = preset("two", base_presets=["org.example.rpp.preset.one"])
    with pytest.raises(ValueError, match="builds on itself.*preset.one -> .*preset.two -> .*preset.one"):
        build(definitions_with([one, two]), ["one"])
    a = profile("a", base_profiles=["org.example.rpp.profile.b"])
    b = profile("b", base_profiles=["org.example.rpp.profile.a"])
    using = preset("using", base_presets=[BASE["id"]], profiles=[a[0]])
    with pytest.raises(ValueError, match="builds on itself"):
        build(definitions_with([using], [a, b]), ["using"])


def test_two_bases_with_different_versions_of_one_extension_stop_the_server():
    left = preset("left", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")])
    right = preset("right", base_presets=[BASE["id"]], extensions=[(RRI, "0.4.0")])
    both = preset("both", base_presets=[left[0], right[0]])

    with pytest.raises(ValueError, match=f"{RRI} in the versions 0.3.0 and 0.4.0"):
        build(definitions_with([left, right, both]), ["both"], held=(RRI,))


def test_a_preset_that_pins_another_version_than_the_proxy_implements_stops_the_server():
    pinned = preset("pinned", extensions=[(RRI, "9.9")])

    with pytest.raises(ValueError, match=f"{RRI} in version 9.9, the proxy implements version 0.3.0"):
        build(definitions_with([pinned]), ["pinned"], held=(RRI,))


def test_an_extension_the_backend_does_not_hold_stops_the_server():
    with pytest.raises(ValueError, match="which the backend does not hold"):
        build(definitions_with([preset("x", extensions=[(RRI, "0.3.0")])]), ["x"])


def test_a_bound_profile_the_preset_lacks_an_extension_of_stops_the_server_and_names_both():
    needing = profile("needing", required=[(RRI, "0.3.0")])
    plain = preset("plain", base_presets=[BASE["id"]])

    with pytest.raises(ValueError, match=f"{needing[0]} requires the extension {RRI}, which the preset {plain[0]} does not contain"):
        build(definitions_with([plain], [needing]), ["plain"], bound={"plain": ["needing"]})


def test_a_requirement_through_a_base_profile_counts():
    needing = profile("needing", required=[(RRI, "0.3.0")])
    building = profile("building", base_profiles=[needing[0]])
    plain = preset("plain", base_presets=[BASE["id"]], profiles=[building[0]])

    with pytest.raises(ValueError, match=f"{building[0]} requires the extension {RRI}"):
        build(definitions_with([plain], [needing, building]), ["plain"])


def test_a_preset_that_has_the_extension_may_bind_the_profile():
    needing = profile("needing", required=[(RRI, "0.3.0")])
    having = preset("having", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")])

    offered = build(definitions_with([having], [needing]), ["having"], bound={"having": ["needing"]}, held=(RRI,))

    assert [p.id for p in offered.offered[0].bound_profiles] == [needing[0]]


def test_a_profile_bound_that_the_preset_already_includes_stops_the_server():
    plain = preset("plain", base_presets=[BASE["id"]], profiles=[ADMIN_ONLY[0]])

    with pytest.raises(ValueError, match="includes the profile .*admin-only, which the server binds to it again"):
        build(definitions_with([plain], [ADMIN_ONLY]), ["plain"], bound={"plain": ["admin-only"]})


@pytest.mark.parametrize("keys, default, bound, message", [
    (["nope"], "nope", {}, "unknown preset nope"),
    (["base", "base"], "base", {}, "offered twice"),
    (["base"], "epp-compatible", {}, "not one of the offered"),
    (["base"], "base", {"epp-compatible": []}, "not an offered preset"),
    (["base"], "base", {"base": ["nope"]}, "unknown profile nope"),
])
def test_a_wrong_choice_stops_the_server(keys, default, bound, message):
    with pytest.raises(ValueError, match=message):
        OfferedPresets.build(Definitions.load(), keys, default, bound, ())


def test_a_reference_to_another_version_than_the_defined_one_stops_the_server():
    wrong = ("org.example.rpp.preset.wrong", {**preset("wrong")[1], "basePresets": [{"id": BASE["id"], "version": "2.0"}]})

    with pytest.raises(ValueError, match="referenced in version 2.0, the definition is version 1.0"):
        build(definitions_with([wrong]), ["wrong"])


def test_an_identifier_denotes_one_definition_only():
    clash = ("org.example.rpp.preset.clash", {**preset("clash")[1], "id": RRI})

    with pytest.raises(ValueError, match="denotes an extension and a preset"):
        definitions_with([clash])


def test_a_profile_schema_that_declares_a_member_neither_rpp_nor_the_preset_has_stops_the_server():
    bad = profile("bad", constraints={"domainName.create": "profile.bad"},
                  defs={"profile.bad": {"properties": {"surprise": {"type": "string"}}}})
    nested = profile("nested", constraints={"domainName.create": "profile.nested"},
                     defs={"profile.nested": {"properties": {"contacts": {"items": {"properties": {"colour": {}}}}}}})

    with pytest.raises(ValueError, match=r"declares \$\.surprise in profile\.bad, which domainName\.create does not declare"):
        build(definitions_with([preset("using", base_presets=[BASE["id"]], profiles=[bad[0]])], [bad]), ["using"])
    with pytest.raises(ValueError, match=r"declares \$\.contacts\[\]\.colour in profile\.nested"):
        build(definitions_with([preset("using", base_presets=[BASE["id"]], profiles=[nested[0]])], [nested]), ["using"])


def test_a_profile_schema_that_constrains_a_definition_that_does_not_exist_stops_the_server():
    bad = profile("ghost", constraints={"ghost.create": "profile.ghost"}, defs={"profile.ghost": {}})

    with pytest.raises(ValueError, match="constrains ghost.create, which does not exist"):
        build(definitions_with([preset("p", base_presets=[BASE["id"]], profiles=[bad[0]])], [bad]), ["p"])


def test_clashing_defs_keys_of_two_profiles_or_with_rpp_stop_the_server():
    other = profile("other", constraints={"domainName.create": "profile.adminOnly"}, defs={"profile.adminOnly": {}})
    both = preset("both", base_presets=[BASE["id"]], profiles=[ADMIN_ONLY[0], other[0]])
    with pytest.raises(ValueError, match="defines profile.adminOnly, which the profile .*admin-only defines"):
        build(definitions_with([both], [ADMIN_ONLY, other]), ["both"])
    shadow = profile("shadow", constraints={"domainName.create": "domainName.read"}, defs={"domainName.read": {}})
    with pytest.raises(ValueError, match="defines domainName.read, which RPP or an extension defines"):
        build(definitions_with([preset("s", base_presets=[BASE["id"]], profiles=[shadow[0]])], [shadow]), ["s"])


def test_a_profile_schema_of_another_profile_or_with_a_pointer_it_lacks_stops_the_server():
    mismatched = profile("mismatched", constraints={"domainName.create": "profile.m"}, defs={"profile.m": {}})
    mismatched[1]["schema"]["rpp:profile"]["id"] = "org.example.rpp.profile.other"
    with pytest.raises(ValueError, match="states rpp:profile"):
        build(definitions_with([preset("m", base_presets=[BASE["id"]], profiles=[mismatched[0]])], [mismatched]), ["m"])


def _extension(**sub):
    return RppExtension(id="x", name="x", version="1.0", url="https://x", extends={"domainName.create": "ext.x"},
                        defs={"ext.x": {"type": "object", **sub}})


def test_the_check_is_made_when_the_presets_are_built(monkeypatch):
    bad = _extension(properties={"a": {}}, anyOf=[{"properties": {"name": {"maxLength": 3}}}])
    monkeypatch.setitem(EXTENSIONS, "x", bad)

    with pytest.raises(ValueError, match="The extension x, definition ext.x uses properties, naming name"):
        build(definitions_with([preset("p", extensions=[("x", "1.0")])]), ["p"], held=("x",))


def test_a_profile_that_constrains_an_extension_it_does_not_require_stops_the_server_naming_both():
    url = EXTENSIONS[RRI].url
    sneaky = profile("sneaky", constraints={}, defs={"profile.s": {"properties": {}}})
    sneaky[1]["schema"]["rpp:constraints"] = {f"{url}#/$defs/ext.rri.domainName.create": "#/$defs/profile.s"}
    having = preset("r", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")], profiles=[sneaky[0]])

    with pytest.raises(ValueError, match=f"{sneaky[0]} constrains ext.rri.domainName.create of the extension {RRI}, "
                                         "which the profile does not require"):
        build(definitions_with([having], [sneaky]), ["r"], held=(RRI,))


def test_a_profile_that_requires_the_extension_may_constrain_it_and_the_composition_holds_it():
    url = EXTENSIONS[RRI].url
    ok = profile("ok", required=[(RRI, "0.3.0")], constraints={}, defs={"profile.s": {"properties": {}}})
    ok[1]["schema"]["rpp:constraints"] = {f"{url}#/$defs/ext.rri.domainName.create": "#/$defs/profile.s"}
    having = preset("r", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")], profiles=[ok[0]])

    offered = build(definitions_with([having], [ok]), ["r"], held=(RRI,)).offered[0]

    from rpp.schema.effective_schema import compose
    composed = compose(offered.extensions, offered.applicable, False, offered.required)
    assert composed["ext.rri.domainName.create"]["allOf"][1] == {"$ref": "#/$defs/profile.s"}


def test_a_base_uri_that_names_a_definition_of_an_extension_stops_the_server():
    mislabel = profile("mislabel", constraints={"ext.rri.domainName.create": "profile.q"}, defs={"profile.q": {}})
    having = preset("r2", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")], profiles=[mislabel[0]])

    with pytest.raises(ValueError, match="constrains ext.rri.domainName.create, which does not exist in RPP"):
        build(definitions_with([having], [mislabel]), ["r2"], held=(RRI,))


def test_an_extension_uri_that_names_a_definition_of_the_base_stops_the_server():
    url = EXTENSIONS[RRI].url
    wrong = profile("wrong", required=[(RRI, "0.3.0")], constraints={}, defs={"profile.w": {}})
    wrong[1]["schema"]["rpp:constraints"] = {f"{url}#/$defs/domainName.create": "#/$defs/profile.w"}
    having = preset("r3", base_presets=[BASE["id"]], extensions=[(RRI, "0.3.0")], profiles=[wrong[0]])

    with pytest.raises(ValueError, match=f"constrains domainName.create, which the extension {RRI} does not define"):
        build(definitions_with([having], [wrong]), ["r3"], held=(RRI,))




def _owned_pair(owner_url="https://example.org/owner.schema.json"):
    owner = RppExtension(id="org.example.owner", name="o", version="1.0", url=owner_url, extends={}, defs={"thing.create": {
        "type": "object", "properties": {"id": {}}}})
    adding = RppExtension(id="org.example.adding", name="a", version="1.0", url="https://example.org/adding.schema.json",
                          extends={"thing.create": "ext.adding"}, owners={"thing.create": owner_url},
                          defs={"ext.adding": {"type": "object", "properties": {"more": {}}}})
    return owner, adding


def test_an_extension_that_extends_another_extension_needs_it_in_the_preset(monkeypatch):
    owner, adding = _owned_pair()
    monkeypatch.setitem(EXTENSIONS, owner.id, owner)
    monkeypatch.setitem(EXTENSIONS, adding.id, adding)
    held = (owner.id, adding.id)
    both = preset("both", base_presets=[BASE["id"]], extensions=[(owner.id, "1.0"), (adding.id, "1.0")])
    alone = preset("alone", base_presets=[BASE["id"]], extensions=[(adding.id, "1.0")])

    assert build(definitions_with([both, alone]), ["both"], held=held).offered[0].extension_ids == (owner.id, adding.id)
    with pytest.raises(ValueError, match="org.example.adding.*extends.*thing.create.*org.example.owner.*alone"):
        build(definitions_with([both, alone]), ["alone"], held=held)


def test_an_extension_that_extends_a_definition_its_owner_lacks_stops_the_server(monkeypatch):
    owner, adding = _owned_pair()
    owner = RppExtension(id=owner.id, name="o", version="1.0", url=owner.url, extends={}, defs={})
    monkeypatch.setitem(EXTENSIONS, owner.id, owner)
    monkeypatch.setitem(EXTENSIONS, adding.id, adding)
    both = preset("both", base_presets=[BASE["id"]], extensions=[(owner.id, "1.0"), (adding.id, "1.0")])

    with pytest.raises(ValueError, match="org.example.adding extends thing.create, which the extension org.example.owner does not define"):
        build(definitions_with([both]), ["both"], held=(owner.id, adding.id))
