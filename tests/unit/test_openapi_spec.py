import yaml

from core.session.session_pool import SessionPool
from tests.helper.profiles import EPP_PROFILE
from rpp.http.app import create_app, OPENAPI_SPEC, parsed_spec


def build_app():
    return create_app(SessionPool(lambda username, password: None), EPP_PROFILE)


def test_apps_share_one_parse_of_the_spec():
    """#112: parsing the OpenAPI document for every app made the unit tests slow."""
    before = parsed_spec.cache_info()
    build_app()
    build_app()
    after = parsed_spec.cache_info()
    assert after.hits + after.misses - before.hits - before.misses == 2
    assert after.misses <= 1


def test_building_an_app_leaves_the_shared_spec_as_parsed():
    """connexion fills in defaults and resolves references in the spec it is given."""
    build_app()
    with OPENAPI_SPEC.open("rb") as spec:
        assert parsed_spec() == yaml.safe_load(spec)


def test_the_app_serves_the_spec():
    response = build_app().test_client().get("/openapi.json")
    assert response.status_code == 200
    assert response.json()["paths"].keys() == parsed_spec()["paths"].keys()
