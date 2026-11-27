"""The planets and satellites of the SQLite demo backend over the wire (config/environments/sqlite-demo.yaml): the paths of the extension, the
authorisation of the sponsor, the transfer of a planet and the messages it queues, and the 501 of the drafts' objects."""
import base64
import dataclasses
import json
import sqlite3

import pytest
from starlette.testclient import TestClient

from core.session.session_pool import SessionPool
from main import compose
from registry_adapter.sqlite.client_directory import ClientDirectory
from registry_adapter.sqlite.common_part import COMMON_PART
from registry_adapter.sqlite.extension_part import load_extension_parts
from registry_adapter.sqlite.sqlite_backend import SqliteBackend
from registry_adapter.sqlite.sqlite_database import SqliteDatabase
from registry_setup import backend_profile, load_registry
from rpp.http.app import create_app
from settings.load_settings import load_settings
from settings.sqlite_settings import SqliteSettings
from tests.helper.test_environment import REPOSITORY

MEDIA_TYPE = "application/rpp+json"
CLIENTS = {"a": ("demo-a", "demo-a-password"), "b": ("demo-b", "demo-b-password")}
SECRET = "Secret-Word1"


@pytest.fixture(scope="module")
def database(tmp_path_factory):
    return tmp_path_factory.mktemp("planets") / "demo.db"


@pytest.fixture(scope="module")
def composition(database):
    """One app over a database file, which the tests empty between them (building an app takes a second)."""
    settings = load_settings(str(REPOSITORY / "config/environments/sqlite-demo.yaml"))
    settings = dataclasses.replace(
        settings, sqlite=SqliteSettings(rpp_sqlite_url=f"sqlite:///{database}",
                                        rpp_sqlite_clients=settings.sqlite.rpp_sqlite_clients))
    composition = compose(settings)
    yield composition
    composition.sessions.close()


@pytest.fixture
def client(composition, database):
    """The client of an app whose database is empty."""
    with sqlite3.connect(database) as connection:
        for table in ("messages", "satellites", "planet_transfers", "planets"):
            connection.execute(f"DELETE FROM {table}")
    return TestClient(composition.app)


def basic(who: str) -> str:
    user, password = CLIENTS[who]
    return "Basic " + base64.b64encode(f"{user}:{password}".encode()).decode("ascii")


def send(client, method, url, who="a", body=None, headers=None, raw=None):
    request_headers = {"Authorization": basic(who), "Accept": MEDIA_TYPE, "RPP-Cltrid": "t-1",
                       "Content-Type": MEDIA_TYPE, **(headers or {})}
    content = raw if raw is not None else (json.dumps(body) if body is not None else None)
    return client.request(method, url, headers=request_headers, content=content)


def planet(name="mars", **members):
    return {"@type": "planet", "id": name, "type": "rocky", "radius": 3389.5,
            "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": SECRET}, **members}


def satellite(name="phobos", of="mars", **members):
    return {"@type": "satellite", "id": name, "planet": {"@type": "planet", "id": of}, "orbitalPeriod": 0.32, **members}


def authorization(secret=SECRET):
    return {"RPP-Authorization": "authinfo value=" + base64.b64encode(secret.encode()).decode("ascii")}


def transfer_request(client, name="mars", who="b", secret=SECRET):
    return send(client, "POST", f"/planets/{name}/processes/transferProcesses", who, {"@type": "transferProcess"},
                authorization(secret))


def code(response) -> str:
    return response.headers["RPP-Code"]


def test_discovery_lists_the_extension_and_the_objects(client):
    document = client.get("/.well-known/rpp", headers={"Accept": MEDIA_TYPE, "RPP-Cltrid": "d-1"}).json()

    assert document["objects"] == ["message", "planet", "satellite"]
    assert "org.example.rpp.extension.planets" in [extension["id"] for extension in document["extensions"]]


class Forbidden:
    """The gateway of an object the backend does not hold, in an app where the stubs must never be what answers."""

    def __getattr__(self, name):
        raise AssertionError(f"The gateway was used ({name}): the preset middleware should have refused the request")


@pytest.fixture(scope="module")
def middleware_only_client():
    """An app whose backend fails the test when a gateway of the drafts' objects is called."""
    settings = load_settings(str(REPOSITORY / "config/environments/sqlite-demo.yaml"))
    registry = load_registry(settings)
    profile = backend_profile(settings, registry)
    parts = load_extension_parts(registry.backend_parts("sqlite"))
    database = SqliteDatabase("sqlite://", [COMMON_PART, *(part.part for part in parts)])
    clients = ClientDirectory(settings.sqlite.rpp_sqlite_clients)

    def backend_of(user, password):
        backend = SqliteBackend(database, clients, profile, parts, user, password)
        backend.domains = backend.contacts = backend.hosts = Forbidden()
        return backend

    sessions = SessionPool(backend_of)
    yield create_app(sessions, profile, discovery_settings=settings.discovery, registry=registry).test_client()
    sessions.close()
    database.close()


@pytest.mark.parametrize("method, path, object_name", [
    ("GET", "/domainNames/example.test", "domainName"), ("GET", "/contacts/c1", "contact"),
    ("GET", "/hosts/ns.example.test", "host"), ("POST", "/contacts", "contact"),
    ("DELETE", "/domainNames/example.test", "domainName"),
])
def test_an_object_of_the_drafts_is_refused_by_the_preset_middleware_before_any_gateway(
        middleware_only_client, method, path, object_name):
    response = send(middleware_only_client, method, path, body={"@type": "contact"} if method == "POST" else None)

    assert response.status_code == 501
    assert code(response) == "02307"
    assert response.json()["detail"] == f"The preset org.example.rpp.preset.planets has no {object_name} object on this server"


def test_a_client_that_is_unknown_or_has_a_wrong_password_is_refused(client):
    wrong = {"Authorization": "Basic " + base64.b64encode(b"demo-a:wrong").decode(), "Accept": MEDIA_TYPE,
             "RPP-Cltrid": "t-1"}
    unknown = {**wrong, "Authorization": "Basic " + base64.b64encode(b"ghost:nope").decode()}

    assert client.get("/planets/mars", headers=wrong).status_code == 401
    assert client.get("/planets/mars", headers=unknown).status_code == 401


@pytest.mark.pyversions
def test_create_and_read_a_planet(client):
    created = send(client, "POST", "/planets", body=planet())

    assert created.status_code == 201
    assert created.headers["Location"].endswith("/planets/mars")
    read = send(client, "GET", "/planets/mars").json()
    assert (read["id"], read["type"], read["radius"]) == ("mars", "rocky", 3389.5)
    assert read["provMetadata"]["spClientId"] == "demo-a"
    assert read["authInfo"]["authdata"] == SECRET
    assert "satellite" not in read


def test_the_auth_info_is_shown_to_the_sponsor_only(client):
    send(client, "POST", "/planets", body=planet())

    assert "authInfo" not in send(client, "GET", "/planets/mars", "b").json()


def test_a_planet_exists_once(client):
    send(client, "POST", "/planets", body=planet())

    assert send(client, "POST", "/planets", body=planet()).status_code == 409


def test_an_unknown_planet_is_404(client):
    assert send(client, "GET", "/planets/nowhere").status_code == 404
    assert send(client, "DELETE", "/planets/nowhere").status_code == 404


@pytest.mark.parametrize("body", [
    {"@type": "planet", "id": "x", "type": "moonlike", "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "a"}},
    {"@type": "planet", "id": "x", "type": "rocky"},
    {"@type": "planet", "id": "x", "type": "rocky", "radius": -1,
     "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "a"}},
    {"@type": "planet", "id": "x", "type": "rocky", "colour": "red",
     "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "a"}},
])
def test_an_invalid_planet_is_400(client, body):
    assert send(client, "POST", "/planets", body=body).status_code == 400


def test_an_unknown_include_element_is_400(client):
    send(client, "POST", "/planets", body=planet())

    assert send(client, "GET", "/planets/mars?includeElements=colour").status_code == 400


def test_availability(client):
    send(client, "POST", "/planets", body=planet())

    free = send(client, "GET", "/planets/venus/availability")
    taken = send(client, "GET", "/planets/mars/availability")
    assert (free.status_code, free.json()["available"]) == (200, True)
    assert (taken.status_code, taken.json()["available"]) == (404, False)
    assert send(client, "HEAD", "/planets/venus/availability").status_code == 200
    assert send(client, "HEAD", "/planets/mars/availability").status_code == 404
    assert send(client, "GET", "/satellites/phobos/availability").json()["@type"] == "satelliteAvailability"


def test_a_full_update_and_a_partial_update(client):
    send(client, "POST", "/planets", body=planet())

    put = send(client, "PUT", "/planets/mars", body={"@type": "planet", "type": "ice-giant", "mass": 2.5})
    assert put.status_code == 200
    assert (put.json()["type"], put.json()["mass"], "radius" in put.json()) == ("ice-giant", 2.5, False)
    assert put.json()["authInfo"]["authdata"] == SECRET  # a full update without authInfo keeps it
    patch = send(client, "PATCH", "/planets/mars", body=[{"op": "replace", "path": "/radius", "value": 10},
                                                         {"op": "remove", "path": "/mass"}])
    assert patch.status_code == 200
    assert (patch.json()["radius"], "mass" in patch.json()) == (10, False)


def test_an_update_that_changes_nothing_is_200(client):
    send(client, "POST", "/planets", body=planet())

    same = send(client, "PUT", "/planets/mars", body={"@type": "planet", "type": "rocky", "radius": 3389.5})

    assert same.status_code == 200


@pytest.mark.parametrize("body", [[{"op": "replace", "path": "/id", "value": "x"}],
                                  [{"op": "remove", "path": "/type"}],
                                  [{"op": "move", "path": "/radius"}]])
def test_a_patch_of_what_cannot_change_is_400(client, body):
    send(client, "POST", "/planets", body=planet())

    assert send(client, "PATCH", "/planets/mars", body=body).status_code == 400


def test_only_the_sponsor_updates_or_deletes(client):
    send(client, "POST", "/planets", body=planet())

    assert send(client, "PUT", "/planets/mars", "b", {"@type": "planet", "type": "gas-giant"}).status_code == 403
    assert send(client, "PATCH", "/planets/mars", "b", [{"op": "replace", "path": "/radius", "value": 1}]).status_code == 403
    assert send(client, "DELETE", "/planets/mars", "b").status_code == 403
    assert send(client, "DELETE", "/planets/mars").status_code == 200
    assert send(client, "GET", "/planets/mars").status_code == 404


def test_a_satellite_is_created_for_a_planet_of_the_client(client):
    send(client, "POST", "/planets", body=planet())

    assert send(client, "POST", "/satellites", "b", satellite()).status_code == 403
    assert send(client, "POST", "/satellites", body=satellite(of="nowhere")).status_code == 404
    created = send(client, "POST", "/satellites", body=satellite())
    assert created.status_code == 201
    assert created.json()["planet"] == {"@type": "planet", "id": "mars"}
    assert created.json()["provMetadata"]["spClientId"] == "demo-a"
    assert send(client, "POST", "/satellites", body=satellite()).status_code == 409


def test_the_satellites_of_a_planet_are_on_demand_and_at_a_direct_access_path(client):
    send(client, "POST", "/planets", body=planet())
    send(client, "POST", "/planets", body=planet("venus"))
    send(client, "POST", "/satellites", body=satellite())

    included = send(client, "GET", "/planets/mars?includeElements=satellite").json()
    assert included["satellite"] == [{"@type": "satellite", "id": "phobos"}]
    assert send(client, "GET", "/planets/mars/satellites/phobos").json()["id"] == "phobos"
    assert send(client, "GET", "/planets/venus/satellites/phobos").status_code == 404
    assert send(client, "GET", "/planets/mars/satellites/deimos").status_code == 404


def test_a_satellite_is_updated_and_deleted_by_its_sponsor(client):
    send(client, "POST", "/planets", body=planet())
    send(client, "POST", "/satellites", body=satellite())

    assert send(client, "PUT", "/satellites/phobos", "b", {"@type": "satellite", "orbitalPeriod": 1}).status_code == 403
    assert send(client, "PUT", "/satellites/phobos", body={"@type": "satellite", "orbitalPeriod": 1}).json()["orbitalPeriod"] == 1
    patched = send(client, "PATCH", "/satellites/phobos", body=[{"op": "replace", "path": "/orbitalPeriod", "value": 2}])
    assert patched.json()["orbitalPeriod"] == 2
    assert send(client, "PATCH", "/satellites/phobos", body=[{"op": "replace", "path": "/planet", "value": 1}]).status_code == 400
    assert send(client, "DELETE", "/satellites/phobos", "b").status_code == 403
    assert send(client, "DELETE", "/satellites/phobos").status_code == 200
    assert send(client, "GET", "/satellites/phobos").status_code == 404


def test_a_planet_with_satellites_is_not_deleted(client):
    send(client, "POST", "/planets", body=planet())
    send(client, "POST", "/satellites", body=satellite())

    refused = send(client, "DELETE", "/planets/mars")

    assert (refused.status_code, code(refused)) == (409, "02305")
    send(client, "DELETE", "/satellites/phobos")
    assert send(client, "DELETE", "/planets/mars").status_code == 200


def test_a_transfer_is_refused_without_the_right_authorisation(client):
    send(client, "POST", "/planets", body=planet())

    for response in (transfer_request(client, secret="wrong"),
                     send(client, "POST", "/planets/mars/processes/transferProcesses", "b", {"@type": "transferProcess"})):
        assert (response.status_code, code(response)) == (401, "02202")
    assert send(client, "GET", "/messages", "a").json() == []


def test_the_sponsor_cannot_request_the_transfer_of_its_own_planet(client):
    send(client, "POST", "/planets", body=planet())

    refused = transfer_request(client, who="a")

    assert (refused.status_code, code(refused)) == (409, "02106")


def test_a_push_transfer_is_refused(client):
    send(client, "POST", "/planets", body=planet())

    response = send(client, "POST", "/planets/mars/processes/transferProcesses", "b",
                    {"@type": "transferProcess", "transferDir": "push", "gainingClientId": "demo-b"}, authorization())

    assert response.status_code in (400, 501)


def test_a_transfer_waits_for_the_sponsor_and_is_approved(client):
    send(client, "POST", "/planets", body=planet())
    send(client, "POST", "/satellites", body=satellite())

    requested = transfer_request(client)

    assert (requested.status_code, code(requested)) == (201, "01001")
    assert requested.json()["trStatus"] == "pending"
    assert requested.headers["Location"].endswith("/transferProcesses/latest")
    again = transfer_request(client)
    assert (again.status_code, code(again)) == (409, "02300")
    for who in "ab":
        queried = send(client, "GET", "/planets/mars/processes/transferProcesses/latest", who)
        assert (queried.status_code, queried.json()["reqClientId"]) == (200, "demo-b")
    assert send(client, "PUT", "/planets/mars", body={"@type": "planet", "type": "gas-giant"}).status_code == 409
    assert send(client, "DELETE", "/planets/mars").status_code == 409
    assert send(client, "POST", "/planets/mars/processes/transferProcesses/latest/transferApprove", "b").status_code == 403
    approved = send(client, "POST", "/planets/mars/processes/transferProcesses/latest/transferApprove", "a")
    assert (approved.status_code, approved.json()["trStatus"]) == (200, "clientApproved")
    assert send(client, "GET", "/planets/mars", "b").json()["provMetadata"]["spClientId"] == "demo-b"
    assert send(client, "GET", "/satellites/phobos", "b").json()["provMetadata"]["spClientId"] == "demo-b"
    assert send(client, "PUT", "/planets/mars", "a", {"@type": "planet", "type": "gas-giant"}).status_code == 403
    assert send(client, "POST", "/planets/mars/processes/transferProcesses/latest/transferApprove", "a").status_code == 409


def test_a_transfer_is_rejected_or_cancelled(client):
    send(client, "POST", "/planets", body=planet())
    transfer_request(client)

    rejected = send(client, "POST", "/planets/mars/processes/transferProcesses/latest/transferReject", "a")
    assert rejected.json()["trStatus"] == "clientRejected"
    assert send(client, "GET", "/planets/mars", "a").json()["provMetadata"]["spClientId"] == "demo-a"
    transfer_request(client)
    assert send(client, "DELETE", "/planets/mars/processes/transferProcesses/latest", "a").status_code == 403
    cancelled = send(client, "DELETE", "/planets/mars/processes/transferProcesses/latest", "b")
    assert cancelled.json()["trStatus"] == "clientCancelled"
    done = send(client, "DELETE", "/planets/mars/processes/transferProcesses/latest", "b")
    assert (done.status_code, code(done)) == (409, "02301")


def test_a_planet_that_was_never_transferred_has_no_transfer_to_query(client):
    send(client, "POST", "/planets", body=planet())

    answer = send(client, "GET", "/planets/mars/processes/transferProcesses/latest", "b")

    assert (answer.status_code, code(answer)) == (409, "02301")


def test_every_transfer_event_queues_a_message_for_the_other_client(client):
    send(client, "POST", "/planets", body=planet())
    transfer_request(client)  # to a: a request
    send(client, "DELETE", "/planets/mars/processes/transferProcesses/latest", "b")  # to a: a cancellation
    transfer_request(client)  # to a: a request
    send(client, "POST", "/planets/mars/processes/transferProcesses/latest/transferReject", "a")  # to b: an outcome

    for_a = send(client, "GET", "/messages", "a")
    assert for_a.headers["RPP-Queue-Size"] == "3"
    first = for_a.json()[0]
    assert first["data"]["@type"] == "transferRequestMessage"
    assert (first["data"]["objectType"], first["data"]["objectId"]) == ("planet", "mars")
    assert send(client, "GET", f"/messages/{first['id']}", "a").status_code == 200
    assert send(client, "DELETE", f"/messages/{first['id']}", "a").status_code == 200
    second = send(client, "GET", "/messages", "a").json()[0]
    assert (second["data"]["@type"], second["data"]["trStatus"]) == ("transferOutcomeMessage", "clientCancelled")
    for_b = send(client, "GET", "/messages", "b").json()[0]
    assert (for_b["data"]["@type"], for_b["data"]["trStatus"]) == ("transferOutcomeMessage", "clientRejected")


def test_a_message_of_another_client_cannot_be_acknowledged(client):
    send(client, "POST", "/planets", body=planet())
    transfer_request(client)
    message = send(client, "GET", "/messages", "a").json()[0]

    assert send(client, "DELETE", f"/messages/{message['id']}", "b").status_code == 404
    assert send(client, "GET", "/messages", "b").json() == []


def drain(client, who):
    """The messages of a client's queue in order, as (type of the data, object type, object id, trStatus), acknowledged."""
    seen = []
    while True:
        head = send(client, "GET", "/messages", who).json()
        if not head:
            return seen
        data = head[0]["data"]
        seen.append((data["@type"], data["objectType"], data["objectId"], data.get("trStatus", data.get("status"))))
        assert send(client, "DELETE", f"/messages/{head[0]['id']}", who).status_code == 200


def planet_with_satellites(client):
    send(client, "POST", "/planets", body=planet())
    for name in ("phobos", "deimos"):
        assert send(client, "POST", "/satellites", body=satellite(name)).status_code == 201


def test_the_satellites_of_a_transferred_planet_queue_no_message_of_their_own(client):
    planet_with_satellites(client)

    transfer_request(client)
    assert send(client, "GET", "/messages", "a").headers["RPP-Queue-Size"] == "1"
    assert send(client, "GET", "/messages", "b").json() == []
    send(client, "POST", "/planets/mars/processes/transferProcesses/latest/transferApprove", "a")

    assert send(client, "GET", "/messages", "b").headers["RPP-Queue-Size"] == "1"
    assert drain(client, "a") == [("transferRequestMessage", "planet", "mars", "pending")]
    assert drain(client, "b") == [("transferOutcomeMessage", "planet", "mars", "clientApproved")]


@pytest.mark.parametrize("answer, who, status, queued", [
    ("transferReject", "a", "clientRejected", {"a": 1, "b": 1}),
    ("cancel", "b", "clientCancelled", {"a": 2, "b": 0}),
])
def test_a_rejected_or_cancelled_transfer_queues_messages_of_the_planet_only(client, answer, who, status, queued):
    planet_with_satellites(client)
    transfer_request(client)
    latest = "/planets/mars/processes/transferProcesses/latest"

    if answer == "cancel":
        send(client, "DELETE", latest, who)
    else:
        send(client, "POST", f"{latest}/{answer}", who)

    messages = {user: drain(client, user) for user in "ab"}
    assert {user: len(found) for user, found in messages.items()} == queued
    assert all(object_type == "planet" and object_id == "mars" for found in messages.values()
               for _kind, object_type, object_id, _status in found)
    assert status in [entry[3] for found in messages.values() for entry in found]


def test_a_message_id_is_ascii_digits_only(client):
    send(client, "POST", "/planets", body=planet())
    transfer_request(client)

    for id in ("١", "٣"):  # ARABIC-INDIC DIGITS ONE and THREE: decimal, but not ASCII
        assert send(client, "DELETE", f"/messages/{id}", "a").status_code == 404
        assert send(client, "GET", f"/messages/{id}", "a").status_code in (404, 501)
    assert send(client, "GET", "/messages", "a").headers["RPP-Queue-Size"] == "1"


def test_the_messages_of_an_empty_queue_are_an_empty_list(client):
    response = send(client, "GET", "/messages", "b")

    assert (response.status_code, response.json()) == (200, [])
