"""#204: the OpenAPI document a deployment serves (`/openapi.json`, `/openapi.yaml`) is OpenAPI 3.1 and carries, for each
operation, the request and response body schemas of the default preset's Preset Schema, the same as `GET /presets/{id}/schema`
publishes it (the members of its extensions and the constraints of its applicable profiles). Connexion validates a body with the
schemas of the preset the request signals, and the results stay those of two-step validation: 400 for a body that breaks the
preset schema, 422 `02308` for one that breaks only a profile constraint."""
import pytest
import yaml

from core.session.session_pool import SessionPool
from rpp.http.app import create_app
from tests.helper.api_docs import served_client
from tests.helper.openapi_documents import (
    CONFIGS,
    MEDIA_TYPE,
    SCHEMAS,
    Server,
    assert_holds_the_preset_schema,
    assert_valid_openapi_3_1,
    definition,
    document,
    in_components,
    p,
    preset_defs,
)
from tests.helper.profiles import EPP_PROFILE, RRI_PROFILE, RRI_REGISTRY


@pytest.fixture(scope="module")
def servers(tmp_path_factory):
    directory = tmp_path_factory.mktemp("openapi")
    built = {name: Server(name, directory) for name in CONFIGS}
    yield built
    for server in built.values():
        server.composition.sessions.close()


@pytest.fixture(scope="module")
def epp():
    return served_client(create_app(SessionPool(lambda username, password: None), EPP_PROFILE))


@pytest.fixture(scope="module")
def rri():
    return served_client(create_app(SessionPool(lambda username, password: None), RRI_PROFILE, registry=RRI_REGISTRY))


def request_ref(doc, path, method="post"):
    return doc["paths"][path][method]["requestBody"]["content"][MEDIA_TYPE]["schema"]["$ref"]


def response_ref(doc, path, method, status):
    return doc["paths"][path][method]["responses"][status]["content"][MEDIA_TYPE]["schema"]["$ref"]



# --- the document is OpenAPI 3.1, valid, and the same as JSON and YAML

def test_the_document_served_is_valid_openapi_3_1(epp, rri):
    assert_valid_openapi_3_1(document(rri))
    assert_valid_openapi_3_1(document(epp))


@pytest.mark.parametrize("name", CONFIGS)
def test_the_document_of_each_demo_configuration_is_valid_openapi_3_1(servers, name):
    assert_valid_openapi_3_1(document(servers[name].client))


def test_the_yaml_is_the_same_document_as_the_json(epp):
    response = epp.get("/openapi.yaml")

    assert response.status_code == 200
    assert yaml.safe_load(response.text) == document(epp)


def test_the_document_names_the_default_preset(servers):
    assert servers["bound"].client.get("/openapi.json").json()["info"]["x-rpp-preset"] == {"id": p("planets"), "version": "1.0"}


# --- the body schemas are the default preset's

def test_a_request_body_of_a_base_object_is_the_definition_of_the_default_preset(epp):
    doc = document(epp)
    defs = preset_defs(epp, "urn:ietf:params:rpp:preset:epp-compatible")

    assert request_ref(doc, "/domainNames") == SCHEMAS + "domainName.create"
    assert definition(doc, request_ref(doc, "/domainNames")) == in_components(defs["domainName.create"])


def test_a_response_body_is_the_definition_of_the_default_preset(epp):
    doc = document(epp)

    assert response_ref(doc, "/domainNames/{name}", "get", "200") == SCHEMAS + "domainName.read"


def test_a_body_of_a_base_object_shows_the_members_of_the_default_presets_extension(rri):
    doc = document(rri)
    defs = preset_defs(rri, "de.denic.rpp.preset.rri")

    created = definition(doc, request_ref(doc, "/domainNames"))
    assert {"$ref": SCHEMAS + "ext.rri.domainName.create"} in created["allOf"]
    assert_holds_the_preset_schema(doc, defs)


def test_the_document_carries_the_constraints_of_the_default_presets_profile(epp):
    doc = document(epp)
    defs = preset_defs(epp, "urn:ietf:params:rpp:preset:epp-compatible")

    assert any(key.startswith("profile.") for key in defs)
    assert_holds_the_preset_schema(doc, defs)


def test_a_bound_profile_of_the_default_preset_is_in_the_document(servers):
    bound = servers["bound"]
    doc = document(bound.client)

    defs = preset_defs(bound.client, p("planets"))

    # The demo leaves out the drafts' objects (`rpp_openapi_omit_*`), and with them the definitions only they refer to: what
    # the document has of the Preset Schema is as published.
    assert "profile.rocky.type" in doc["components"]["schemas"]
    assert_holds_the_preset_schema(doc, {key: schema for key, schema in defs.items() if key in doc["components"]["schemas"]})
    assert definition(doc, request_ref(doc, "/planets")) == in_components(defs["planet.create"])


def test_an_extension_path_has_the_definitions_of_the_extension_not_plain_objects(servers):
    extended = servers["extended"]
    doc = document(extended.client)
    defs = preset_defs(extended.client, p("planets-complete"))

    assert request_ref(doc, "/planets") == SCHEMAS + "planet.create"
    assert definition(doc, request_ref(doc, "/planets")) == in_components(defs["planet.create"])
    assert {"$ref": SCHEMAS + "ext.atmosphere.planet.create"} in definition(doc, request_ref(doc, "/planets"))["allOf"]
    assert response_ref(doc, "/planets/{id}", "get", "200") == SCHEMAS + "planet.read"


def test_an_extension_object_of_the_drafts_extension_has_its_definition(rri):
    doc = document(rri)

    assert request_ref(doc, "/requestContacts") == SCHEMAS + "ext.rri.requestContact.create"


def test_a_body_without_a_definition_in_the_preset_schema_stays_as_generated(epp):
    doc = document(epp)

    assert request_ref(doc, "/domainNames/{name}", "patch") == SCHEMAS + "protocol.PartialUpdate"
    assert "protocol.PartialUpdate" in doc["components"]["schemas"]


def test_the_generated_body_schemas_replaced_are_not_left_in_the_document(epp):
    schemas = document(epp)["components"]["schemas"]

    assert "gen.domainName.create" not in schemas and "gen.domainName.read" not in schemas


def test_two_configurations_with_other_default_presets_have_other_documents(servers):
    bare, extended = document(servers["bare"].client), document(servers["extended"].client)

    assert "ext.atmosphere.planet.create" in extended["components"]["schemas"]
    assert "ext.atmosphere.planet.create" not in bare["components"]["schemas"]
    assert definition(bare, request_ref(bare, "/planets")) != definition(extended, request_ref(extended, "/planets"))


# --- validation follows the signalled preset; the results of two-step validation stay

ATMOSPHERE = {"@type": "atmosphere", "pressure": 1.0}


def planet(name, **members):
    return {"@type": "planet", "id": name, "type": "rocky", "radius": 3389.5,
            "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "Secret-Word1"}, **members}


def test_a_request_under_another_preset_than_the_default_is_validated_with_its_own_schemas(servers):
    """The bound default is planets: an atmosphere is a member of planets-atmosphere only."""
    bound = servers["bound"]

    created = bound.post("/planets", planet("oas-other", atmosphere=ATMOSPHERE), "planets-atmosphere")

    assert created.status_code == 201, created.text
    read = bound.get("/planets/oas-other", "planets-atmosphere")
    assert read.status_code == 200, read.text
    assert read.json()["atmosphere"]["pressure"] == 1.0


def test_a_member_outside_the_signalled_preset_is_a_400(servers):
    response = servers["bound"].post("/planets", planet("oas-outside", atmosphere=ATMOSPHERE), "planets")

    assert response.status_code == 400, response.text
    assert response.headers["RPP-Code"] == "02001"


def test_a_body_that_breaks_the_preset_schema_is_a_400_also_where_a_profile_applies(servers):
    response = servers["bound"].post("/planets", planet("oas-bad", radius="big", type="gas-giant"), "planets")

    assert response.status_code == 400, response.text
    assert response.headers["RPP-Code"] == "02001"


def test_a_body_that_breaks_only_a_profile_constraint_is_a_422_with_the_profile(servers):
    response = servers["bound"].post("/planets", planet("oas-gas", type="gas-giant"), "planets")

    assert response.status_code == 422, response.text
    error = response.json()["errors"][0]
    assert response.headers["RPP-Code"] == "02308" and error["profile"] == "org.example.rpp.profile.rocky-planets"


def test_a_body_of_another_type_is_a_400_with_02001(servers):
    response = servers["bare"].post("/planets", {**planet("oas-type"), "@type": "satellite"}, "planets")

    assert response.status_code == 400, response.text
    assert response.headers["RPP-Code"] == "02001"
