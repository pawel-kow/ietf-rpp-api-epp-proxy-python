"""The preset rri-strict over the wire of the app composed for RRI (docs/rri/rri-strict-preset.md): the DENIC RRI profile
(docs/rri/rri-profile.md) refuses what the registry cannot hold with 422 `02308`, the preset rri and a request that names none
are unchanged, and discovery lists the preset and the profile."""
import pytest

from core.session.session_pool import SessionPool
from rpp.http.app import create_app
from tests.helper.api_docs import served_client
from tests.helper.fake_rri_client import FakeRriClient, reply, rri_backends
from tests.helper.profiles import RRI_PROFILE, RRI_REGISTRY
from tests.unit.test_rri_adapter import DOMAIN_INFO, NAME
from tests.unit.test_rri_wire import BODY_HEADERS, DISCOVERY, HEADERS

RRI = "de.denic.rpp.preset.rri"
STRICT = "de.denic.rpp.preset.rri-strict"
PROFILE = "de.denic.rpp.profile.rri"

HOLDER = {"@type": "contact", "id": "DENIC-1000022-HOLDER"}
DNS = {"@type": "dnsData", "records": [{"@type": "dnsRecord", "name": "@", "type": "a", "rdata": {"address": "192.0.2.10"}}]}
CREATE = {"@type": "domainName", "name": NAME, "registrant": HOLDER, "dns": DNS}

PROFILE_WITH_STRICT = RRI_PROFILE.with_changes({"presets": ["base", "rri", "rri-strict"]})


def named(preset, headers=BODY_HEADERS):
    return {**headers, "RPP-Preset": f"preset={preset};version=1.0"}


def setup(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeRriClient(username, password, replies=list(replies)))
        return clients[-1]

    app = create_app(SessionPool(rri_backends(factory)), PROFILE_WITH_STRICT, discovery_settings=DISCOVERY, registry=RRI_REGISTRY)
    return app.test_client(), clients


def nothing_sent(clients):
    return all(not client.sent for client in clients)


def body(**changes):
    return {key: value for key, value in {**CREATE, **changes}.items() if value is not None}


@pytest.mark.parametrize("changes", [
    {"registrant": None},
    {"contacts": [{"label": "tech", "object": {"@type": "contact", "id": "DENIC-1000022-TECH"}}]},
    {"nameservers": [{"@type": "host", "hostName": "ns1.example.com"}]},
], ids=["no registrant", "a tech label", "nameservers"])
def test_a_create_the_profile_refuses_is_a_422_before_any_command(changes):
    client, clients = setup()

    response = client.post("/domainNames", json=body(**changes), headers=named(STRICT))

    assert response.status_code == 422, response.text
    assert response.headers["RPP-Code"] == "02308"
    assert response.headers["RPP-Preset"] == f"preset={STRICT};version=1.0"
    assert nothing_sent(clients)


@pytest.mark.parametrize("preset", [RRI, STRICT])
@pytest.mark.parametrize("role", ["generalRequest", "abuse"])
def test_a_request_contact_role_as_a_label_is_unsupported_under_every_preset(preset, role):
    """The extension defines the roles as members of their own: its refusal (501 02102) runs before step 2 of the validation,
    so it is not a broken constraint of the profile (core, Extensions and Profiles of a Request)."""
    client, clients = setup()
    contacts = [{"label": role, "object": {"@type": "contact", "id": "DENIC-1000022-GR"}}]

    response = client.post("/domainNames", json=body(contacts=contacts), headers=named(preset))

    assert (response.status_code, response.headers["RPP-Code"]) == (501, "02102")
    assert nothing_sent(clients)


@pytest.mark.parametrize("preset", [RRI, STRICT])
def test_a_full_update_with_a_request_contact_role_as_a_label_is_unsupported_under_every_preset(preset):
    client, clients = setup()
    put = {"@type": "domainName", "registrant": HOLDER, "dns": DNS,
           "contacts": [{"label": "abuse", "object": {"@type": "contact", "id": "DENIC-1000022-GR"}}]}

    response = client.put(f"/domainNames/{NAME}", json=put, headers=named(preset))

    assert (response.status_code, response.headers["RPP-Code"]) == (501, "02102")
    assert nothing_sent(clients)


def test_a_patch_that_removes_the_registrant_is_refused_by_the_profile():
    """The profile requires the registrant of the update definition: its removal is a broken constraint, though the object read
    for the patch is not constrained (a read of a foreign domain has no registrant)."""
    client, clients = setup(DOMAIN_INFO)

    response = client.patch(f"/domainNames/{NAME}", json=[{"op": "remove", "path": "/registrant"}], headers=named(STRICT))

    assert response.status_code == 422, response.text
    assert response.headers["RPP-Code"] == "02308"
    assert response.json()["errors"][0]["profile"] == PROFILE
    assert len(clients[0].sent) <= 1      # at most the read of the domain, no update


def test_a_patch_that_removes_the_registrant_is_unchanged_under_the_rri_preset():
    client, clients = setup(DOMAIN_INFO, DOMAIN_INFO, reply(), DOMAIN_INFO)

    response = client.patch(f"/domainNames/{NAME}", json=[{"op": "remove", "path": "/registrant"}], headers=named(RRI))

    assert (response.status_code, response.headers["RPP-Code"]) == (202, "01000")
    assert ["<domain:info" in command for command in clients[0].sent] == [True, False, True]   # the read, the update, the read back


def test_a_full_update_without_a_registrant_is_a_422():
    client, clients = setup()
    put = {key: value for key, value in CREATE.items() if key not in ("name", "registrant")}

    response = client.put(f"/domainNames/{NAME}", json=put, headers=named(STRICT))

    assert response.status_code == 422, response.text
    assert response.headers["RPP-Code"] == "02308"
    assert nothing_sent(clients)


NAMESERVER = {"op": "add", "path": "/nameservers", "value": {"@type": "host", "hostName": "ns1.example.com"}}
TECH = {"op": "add", "path": "/contacts", "value": {"label": "tech", "object": {"@type": "contact", "id": "DENIC-1000022-TECH"}}}
ABUSE = {"op": "add", "path": "/contacts", "value": {"label": "abuse", "object": {"@type": "contact", "id": "DENIC-1000022-GR"}}}


@pytest.mark.parametrize("operation", [NAMESERVER, TECH], ids=["a nameserver", "a tech contact"])
@pytest.mark.parametrize("preset", [RRI, STRICT])
def test_a_patch_the_backend_cannot_hold_is_unsupported_before_the_profile_is_checked(preset, operation):
    """Open (review round 1, item 1): the spec says 422 02308 under rri-strict; the conversion that needs no read runs first
    (test_patch_alike_under_profiles_wire.py), so the answer is the same as under rri and nothing is sent."""
    client, clients = setup(DOMAIN_INFO)

    response = client.patch(f"/domainNames/{NAME}", json=[operation], headers=named(preset))

    assert (response.status_code, response.headers["RPP-Code"]) == (501, "02102")
    assert not clients[0].sent


@pytest.mark.parametrize("preset", [RRI, STRICT])
def test_a_patch_that_adds_a_request_contact_role_as_a_label_is_unsupported_under_every_preset(preset):
    client, clients = setup(DOMAIN_INFO)

    response = client.patch(f"/domainNames/{NAME}", json=[ABUSE], headers=named(preset))

    assert (response.status_code, response.headers["RPP-Code"]) == (501, "02102")
    assert len(clients[0].sent) <= 1


def test_a_create_the_profile_accepts_is_sent():
    client, clients = setup(reply(), DOMAIN_INFO)

    response = client.post("/domainNames", json=CREATE, headers=named(STRICT))

    assert response.status_code == 201, response.text
    assert "<domain:create>" in clients[0].sent[0]


def test_the_host_operations_keep_their_501_under_the_strict_preset():
    client, clients = setup()

    response = client.get("/hosts/ns1.example.de", headers=named(STRICT, HEADERS))

    assert response.status_code == 501 and response.headers["RPP-Code"] == "02307"
    assert nothing_sent(clients)


@pytest.mark.parametrize("headers", [BODY_HEADERS, named(RRI)], ids=["no preset", "rri"])
@pytest.mark.parametrize("changes, status, code", [
    ({"contacts": [{"label": "tech", "object": {"@type": "contact", "id": "DENIC-1000022-TECH"}}]}, 501, "02102"),
    ({"nameservers": [{"@type": "host", "hostName": "ns1.example.com"}]}, 501, "02102"),
])
def test_the_rri_preset_and_a_request_without_one_keep_their_answers(headers, changes, status, code):
    client, clients = setup()

    response = client.post("/domainNames", json=body(**changes), headers=headers)

    assert (response.status_code, response.headers["RPP-Code"]) == (status, code)
    assert response.headers["RPP-Preset"] == f"preset={RRI};version=1.0"
    assert nothing_sent(clients)


@pytest.mark.parametrize("headers", [BODY_HEADERS, named(RRI)], ids=["no preset", "rri"])
def test_a_create_without_a_registrant_is_sent_under_the_rri_preset(headers):
    client, clients = setup(reply(), DOMAIN_INFO)

    response = client.post("/domainNames", json=body(registrant=None), headers=headers)

    assert (response.status_code, response.headers["RPP-Code"]) == (201, "01000")
    assert "<domain:create>" in clients[0].sent[0] and "role=\"holder\"" not in clients[0].sent[0]


def test_discovery_lists_the_strict_preset_with_its_profile_and_extension():
    client, _ = setup()

    found = client.get("/.well-known/rpp", headers=HEADERS).json()
    listed = {item["id"]: item for item in found["presets"]}

    assert {RRI, STRICT} <= set(listed)
    assert [profile["id"] for profile in listed[STRICT]["profiles"]] == [PROFILE]
    assert listed[RRI]["profiles"] == []
    assert PROFILE in {profile["id"] for profile in found["profiles"]}
    assert client.get(f"/presets/{STRICT}", headers=HEADERS).status_code == 200
    assert client.get(f"/profiles/{PROFILE}", headers=HEADERS).status_code == 200


def test_no_served_document_carries_the_module_of_a_handler():
    """`x-openapi-router-controller` routes the operations of the request contact to their handlers; it is internal, so the
    document of the default preset and that of each offered preset leave it out, while the operations stay."""
    app = create_app(SessionPool(rri_backends(lambda u, p: FakeRriClient(u, p, replies=[]))), PROFILE_WITH_STRICT,
                     discovery_settings=DISCOVERY, registry=RRI_REGISTRY)
    client = served_client(app)

    for url in ("/openapi.json", *(f"/openapi/{preset}.json" for preset in (RRI, STRICT))):
        response = client.get(url)
        assert response.status_code == 200, url
        assert "x-openapi-router-controller" not in response.text, url
        assert response.json()["paths"]["/requestContacts"]["post"]["operationId"] == "requestContacts_create", url
