"""The presets over the wire: the Preset and Profile Data Objects, discovery, the selected preset and what it allows."""
import pytest

from core.session.session_pool import SessionPool
from rpp.http.app import create_app
from rpp.http.header_preset_signalling import HeaderPresetSignalling
from rpp.http.preset_selection import PresetSelection
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient
from tests.helper.fake_rri_client import FakeRriClient, rri_backends
from tests.helper.presets import BASE, EPP, EPP_COMPATIBILITY, EPP_PRESETS, RRI, RRI_PRESETS
from tests.helper.profiles import EPP_PROFILE, RRI_PROFILE, RRI_REGISTRY
from tests.unit.test_rri_wire import DISCOVERY, HEADERS, MEDIA_TYPE


def epp_client(profile=EPP_PROFILE):
    sessions = SessionPool(epp_backends(lambda username, password: FakeEppClient(username, password)))
    return create_app(sessions, profile, discovery_settings=DISCOVERY).test_client()


def rri_client(profile=RRI_PROFILE):
    sessions = SessionPool(rri_backends(lambda username, password: FakeRriClient(username, password, replies=[])))
    return create_app(sessions, profile, discovery_settings=DISCOVERY, registry=RRI_REGISTRY).test_client()


def read(client, identifier, path="/presets"):
    return client.get(f"{path}/{identifier}", headers=HEADERS)


def test_the_base_preset_is_read_with_no_extension_and_no_profile():
    response = read(epp_client(), BASE)

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json() == {
        "@type": "preset", "id": BASE, "name": "Base preset", "version": "1.0", "rppVersion": "1.0",
        "description": "RPP without extensions and without profiles.", "defaultPreset": False,
        "url": "https://datatracker.ietf.org/doc/draft-ietf-rpp-data-objects/",
        "extensions": [], "profiles": [], "boundProfiles": [],
    }


def test_the_epp_compatible_preset_is_the_default_and_has_the_epp_compatibility_profile_and_a_base():
    body = read(epp_client(), EPP).json()

    assert body["defaultPreset"] is True
    assert body["basePresets"] == [{"@type": "preset", "id": BASE, "version": "1.0"}]
    assert body["profiles"] == [{"@type": "profile", "id": EPP_COMPATIBILITY, "version": "1.0"}]
    assert body["boundProfiles"] == [] and body["extensions"] == []
    assert "schema" not in body       # onDemand


def test_the_schema_is_embedded_when_the_request_includes_it():
    response = epp_client().get(f"/presets/{EPP}?includeElements=schema", headers=HEADERS)

    assert response.status_code == 200
    assert response.json()["schema"]["rpp:preset"] == {"id": EPP, "version": "1.0"}


def test_the_rri_preset_has_the_rri_extension():
    body = read(rri_client(), RRI).json()

    assert body["defaultPreset"] is True
    assert [(e["id"], e["version"]) for e in body["extensions"]] == [("de.denic.rpp.rri", "0.3.0")]
    assert body["url"] == "https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/blob/main/docs/rri/rri-preset.md"


def test_a_preset_reads_the_same_on_every_server_but_for_the_default():
    on_epp, on_rri = read(epp_client(), BASE).json(), read(rri_client(), BASE).json()

    assert on_epp == on_rri


def test_the_profile_is_read_with_its_url_and_no_required_extension():
    response = read(epp_client(), EPP_COMPATIBILITY, "/profiles")

    assert response.status_code == 200
    assert response.json() == {
        "@type": "profile", "id": EPP_COMPATIBILITY, "name": "EPP Compatibility Profile", "version": "1.0",
        "rppVersion": "1.0", "requiredExtensions": [],
        "description": "Constrains RPP to what EPP can represent, for a server that provisions a repository through RPP "
                       "and EPP concurrently.",
        "url": "https://datatracker.ietf.org/doc/draft-kowalik-rpp-epp-compatibility/",
    }


@pytest.mark.parametrize("client, identifier, path", [
    (epp_client(), RRI, "/presets"), (rri_client(), EPP, "/presets"), (epp_client(), "nope", "/presets"),
    (rri_client(), EPP_COMPATIBILITY, "/profiles"),       # no preset of this server has the profile
])
def test_a_preset_or_profile_the_server_does_not_offer_is_a_404(client, identifier, path):
    response = read(client, identifier, path)

    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"


@pytest.mark.parametrize("path", ["/presets/" + BASE, "/profiles/" + EPP_COMPATIBILITY])
def test_a_preset_or_profile_needs_authentication(path):
    assert epp_client().get(path, headers={"Accept": MEDIA_TYPE}).status_code == 401


def test_discovery_states_the_offered_presets_their_profiles_and_extensions():
    epp = epp_client().get("/.well-known/rpp", headers=HEADERS).json()
    rri = rri_client().get("/.well-known/rpp", headers=HEADERS).json()

    assert [(p["id"], p["version"], p["defaultPreset"]) for p in epp["presets"]] == [(BASE, "1.0", False), (EPP, "1.0", True)]
    assert epp["presets"][1]["profiles"] == [{"@type": "profile", "id": EPP_COMPATIBILITY, "version": "1.0"}]
    assert epp["presets"][1]["boundProfiles"] == [] and "schema" not in epp["presets"][1]
    assert epp["profiles"] == [{"@type": "profile", "id": EPP_COMPATIBILITY, "version": "1.0"}]
    assert "extensions" not in epp
    assert epp["objects"] == ["domainName", "host", "contact", "message"]
    assert [p["id"] for p in rri["presets"]] == [BASE, RRI]
    assert [e["id"] for e in rri["extensions"]] == ["de.denic.rpp.rri"]
    assert "profiles" not in rri
    assert rri["objects"] == ["domainName", "contact", "organisation", "message", "requestContact"]
    assert "profileSchemas" not in epp


def test_the_default_preset_is_selected_and_an_object_the_backend_lacks_is_refused_before_any_command():
    response = rri_client().get("/hosts/ns1.example.de", headers=HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02307"
    assert "rri" in response.json()["detail"]


def test_a_request_that_is_not_authenticated_is_a_401_not_a_hint_of_the_presets():
    response = rri_client().get("/hosts/ns1.example.de", headers={"Accept": MEDIA_TYPE})

    assert response.status_code == 401


def test_a_path_no_operation_serves_stays_a_404_even_under_an_object_the_backend_lacks():
    response = rri_client().get("/hosts/a/b/c/d", headers={"Accept": MEDIA_TYPE})

    assert response.status_code == 404


def test_the_extension_paths_exist_for_the_extensions_of_an_offered_preset_only():
    assert epp_client().get("/requestContacts/X-1", headers=HEADERS).status_code == 404


class Selecting:
    """Stands for a signalling method: the resolver is the one place a preset is chosen."""

    def __init__(self, monkeypatch, preset_id, presets=RRI_PRESETS):
        selected = presets.by_id(preset_id)
        monkeypatch.setattr(HeaderPresetSignalling, "resolve", lambda self, scope: PresetSelection.of(selected))


def test_an_object_of_an_extension_outside_the_preset_is_a_400_like_any_content_that_does_not_conform(monkeypatch):
    Selecting(monkeypatch, BASE)
    client = rri_client()

    # core RC4: the extension's object is outside base. The code is the one a schema failure has (02001).
    refused = client.get("/requestContacts/DENIC-1000022-GR", headers=HEADERS)
    assert refused.status_code == 400 and refused.headers["RPP-Code"] == "02001"
    # An extension member is undeclared under base: the combined schema holds only the preset's extensions.
    body = {"@type": "domainName", "name": "foo.de", "generalRequest": {"@type": "requestContact", "id": "X-1"}}
    rejected = client.post("/domainNames", json=body, headers={**HEADERS, "Content-Type": MEDIA_TYPE})
    assert rejected.status_code == 400
