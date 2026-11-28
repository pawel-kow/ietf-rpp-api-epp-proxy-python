"""#204: two switches leave out of the OpenAPI document served what the server does not implement, which the drafts' API
contract lists (a deviation from it, so each is off by default). `rpp_openapi_omit_unheld_objects` leaves out the operations on
the data objects the backend does not hold under the default preset (they answer 501 `02307`), `rpp_openapi_omit_unimplemented`
the operations no handler serves (501 `02101`). Routing is unchanged: those requests still answer 501."""
import base64
import dataclasses
from types import SimpleNamespace

import pytest
from openapi_spec_validator import OpenAPIV31SpecValidator
from openapi_spec_validator.validation.exceptions import ExtraParametersError
from starlette.testclient import TestClient

from core.session.session_pool import SessionPool
from main import compose
from rpp.http.app import create_app
from tests.helper.api_docs import served_client
from settings.load_settings import load_settings
from settings.openapi_settings import OpenApiSettings
from settings.sqlite_settings import SqliteSettings
from tests.helper.profiles import EPP_PROFILE, RRI_PROFILE, RRI_REGISTRY
from tests.helper.test_environment import REPOSITORY

BASIC = "Basic " + base64.b64encode(b"demo-a:demo-a-password").decode()
DRAFT_OBJECTS = ("/domainNames", "/contacts", "/hosts")


def app(profile, unheld=False, unimplemented=False, registry=None):
    switches = SimpleNamespace(rpp_openapi_omit_unheld_objects=unheld, rpp_openapi_omit_unimplemented=unimplemented)
    return served_client(create_app(SessionPool(lambda username, password: None), profile, openapi_settings=switches,
                                  registry=registry))


def paths(client):
    return client.get("/openapi.json").json()["paths"]


def operation_ids(client):
    return {operation["operationId"] for item in paths(client).values() for operation in item.values()
            if isinstance(operation, dict) and "operationId" in operation}


def valid(doc):
    return [str(error) for error in OpenAPIV31SpecValidator(doc).iter_errors() if not isinstance(error, ExtraParametersError)]


@pytest.fixture(scope="module")
def demo(tmp_path_factory):
    settings = load_settings(str(REPOSITORY / "config/environments/sqlite-demo.yaml"))
    settings = dataclasses.replace(settings, sqlite=SqliteSettings(
        rpp_sqlite_url=f"sqlite:///{tmp_path_factory.mktemp('omit') / 'demo.db'}",
        rpp_sqlite_clients=settings.sqlite.rpp_sqlite_clients))
    composition = compose(settings)
    yield TestClient(composition.app)
    composition.sessions.close()


# --- the settings

def test_both_switches_are_off_by_default():
    assert OpenApiSettings() == OpenApiSettings(rpp_openapi_omit_unheld_objects=False, rpp_openapi_omit_unimplemented=False)
    assert load_settings(str(REPOSITORY / "config/environments/epp-docker.yaml")).openapi == OpenApiSettings()


@pytest.mark.parametrize("key", ["rpp_openapi_omit_unheld_objects", "rpp_openapi_omit_unimplemented"])
def test_a_switch_that_is_not_a_boolean_stops_the_configuration(key):
    with pytest.raises(ValueError, match=key):
        OpenApiSettings(**{key: "yes"})


@pytest.mark.parametrize("name", ["config/environments/sqlite-demo.yaml", "config/environments/sqlite-demo-extended.yaml", "config/environments/sqlite-demo-bound.yaml",
                                  "config/environments/sqlite-demo-inherit.yaml"])
def test_the_demo_configurations_switch_both_on(name):
    assert load_settings(str(REPOSITORY / name)).openapi == OpenApiSettings(True, True)


# --- off: the document has every operation

def test_without_the_switches_the_document_has_every_path_of_the_contract():
    client = app(EPP_PROFILE)

    assert {"/organisations", "/domainNames/{name}/processes"} <= paths(client).keys()


# --- the objects the backend does not hold

def test_the_operations_on_objects_the_backend_does_not_hold_are_left_out():
    found = paths(app(RRI_PROFILE, unheld=True, registry=RRI_REGISTRY))

    assert not [path for path in found if path.startswith("/hosts")]
    assert "/domainNames" in found and "/contacts" in found and "/requestContacts" in found


def test_an_object_the_backend_holds_stays():
    assert paths(app(EPP_PROFILE, unheld=True)).keys() == paths(app(EPP_PROFILE)).keys()


# --- the operations no handler serves

def test_the_operations_no_handler_serves_are_left_out():
    ids = operation_ids(app(EPP_PROFILE, unimplemented=True))

    assert "domainNames_create" in ids and "domainNameTransferProcesses_transferCreate" in ids
    assert "domainNameCreateProcesses_list" not in ids
    assert not [path for path in paths(app(EPP_PROFILE, unimplemented=True)) if path.startswith("/organisations")]


def test_a_path_keeps_the_operations_a_handler_serves():
    found = paths(app(EPP_PROFILE, unimplemented=True))

    assert "post" in found["/domainNames/{name}/processes/transferProcesses"]
    assert "get" not in found["/domainNames/{name}/processes/transferProcesses"]


def test_each_switch_alone_leaves_out_only_its_own():
    unheld, unimplemented = paths(app(RRI_PROFILE, unheld=True, registry=RRI_REGISTRY)), paths(app(RRI_PROFILE, unimplemented=True, registry=RRI_REGISTRY))

    assert "/organisations" in unheld
    assert [path for path in unimplemented if path.startswith("/hosts")]


# --- the demo: planets and satellites only, and the routing as before

def test_the_demo_document_shows_none_of_the_drafts_objects(demo):
    found = paths(demo)

    assert not [path for path in found if path.startswith(DRAFT_OBJECTS + ("/organisations",))]
    assert {"/planets", "/satellites/{id}", "/messages", "/presets/{id}", "/.well-known/rpp"} <= found.keys()


def test_the_demo_document_is_valid_openapi_3_1_and_keeps_no_schema_of_what_it_left_out(demo):
    doc = demo.get("/openapi.json").json()

    assert valid(doc) == []
    assert "domainName.create" not in doc["components"]["schemas"]


def test_a_path_left_out_of_the_document_still_answers_501(demo):
    response = demo.get("/domainNames/example.test", headers={
        "Authorization": BASIC, "RPP-Cltrid": "omit-1", "RPP-Preset": "preset=org.example.rpp.preset.planets;version=1.0"})

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02307"
