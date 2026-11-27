import pytest
from jsonschema import ValidationError

from core.model.shared.discovery import Discovery
from rpp.mapping.discovery import discovery
from tests.helper.presets import EPP_PRESETS, RRI_PRESETS

# the tests map without an app, so a validator is built on first use (SchemaScope.of)


def a_discovery(**changes):
    values = dict(
        version="1.0", base_url="https://rpp.example/rpp", tlds=["example"], environment_name="rpp.example",
        environment_status="test", objects=["domainName", "host", "contact"], datetime="2026-05-31T12:30:00Z",
    )
    return Discovery(**{**values, **changes})


def test_all_required_members():
    rpp = discovery.model_to_rpp(a_discovery(), EPP_PRESETS)

    assert {key: rpp[key] for key in ("@type", "versions", "environment", "tlds", "objects", "datetime")} == {
        "@type": "discovery",
        "versions": [{"@type": "discoveryVersion", "version": "1.0", "baseUrl": "https://rpp.example/rpp"}],
        "environment": {"@type": "discoveryEnvironment", "name": "rpp.example", "status": "test"},
        "tlds": ["example"],
        "objects": ["domainName", "host", "contact"],
        "datetime": "2026-05-31T12:30:00Z",
    }
    assert [(p["id"], p["version"], p["defaultPreset"]) for p in rpp["presets"]] == [
        ("urn:ietf:params:rpp:preset:base", "1.0", False), ("urn:ietf:params:rpp:preset:epp-compatible", "1.0", True)]
    assert rpp["profiles"] == [{"@type": "profile", "id": "urn:ietf:params:rpp:profile:epp-compatibility", "version": "1.0"}]


def test_a_preset_entry_has_its_extensions_profiles_and_bound_profiles_and_no_schema():
    entry = discovery.model_to_rpp(a_discovery(), EPP_PRESETS)["presets"][1]

    assert entry["extensions"] == [] and entry["boundProfiles"] == []
    assert entry["profiles"] == [{"@type": "profile", "id": "urn:ietf:params:rpp:profile:epp-compatibility", "version": "1.0"}]
    assert "schema" not in entry


def test_no_tlds_is_invalid():
    with pytest.raises(ValidationError):
        discovery.model_to_rpp(a_discovery(tlds=[]), EPP_PRESETS)


def test_an_offered_extension_is_described():
    """Json §6.2.12, from the extension's schema file."""
    extensions = discovery.model_to_rpp(a_discovery(), RRI_PRESETS)["extensions"]

    assert extensions == [{"@type": "extension", "name": "DENIC RRI", "id": "de.denic.rpp.rri", "version": "0.3.0",
                           "url": "https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/.spec/"
                                  "rri-extension.schema.json"}]
