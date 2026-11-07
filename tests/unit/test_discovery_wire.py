import logging
import re
from types import SimpleNamespace

import pytest

from app import create_app
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"
HEADERS = {"Accept": MEDIA_TYPE, "RPP-Cltrid": "disc-wire-1"}
SETTINGS = SimpleNamespace(
    rpp_base_url="https://rpp.example/rpp", rpp_tlds=["example", "test"],
    rpp_environment_name="rpp.example", rpp_environment_status="test",
)
FACTORY_CALLS = []


class NoEppAuthenticator:
    """Fails the test if discovery asks for a session."""

    def authenticate(self, username, password):
        FACTORY_CALLS.append((username, password))
        return None


def app_with(settings):
    return create_app(NoEppAuthenticator(), discovery_settings=settings).test_client()


@pytest.fixture(scope="module")
def client():
    return app_with(SETTINGS)


def test_discovery_needs_no_authentication(client):
    response = client.get("/.well-known/rpp", headers=HEADERS)

    assert response.status_code == 200
    assert response.headers["Content-Type"].startswith(MEDIA_TYPE)
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Cltrid"] == "disc-wire-1"
    assert response.headers["RPP-Svtrid"]


def test_discovery_never_asks_for_an_epp_session(client):
    client.get("/.well-known/rpp", headers=HEADERS)

    assert FACTORY_CALLS == []


def test_discovery_ignores_credentials_it_does_not_need(client):
    response = client.get("/.well-known/rpp", headers={**HEADERS, "Authorization": "Basic dXNlcjpwdw=="})

    assert response.status_code == 200
    assert FACTORY_CALLS == []


def test_discovery_states_what_the_proxy_is_configured_and_built_for(client):
    body = client.get("/.well-known/rpp", headers=HEADERS).json()

    assert body["@type"] == "discovery"
    assert body["versions"] == [{"@type": "discoveryVersion", "version": "1.0", "baseUrl": "https://rpp.example/rpp"}]
    assert body["environment"] == {"@type": "discoveryEnvironment", "name": "rpp.example", "status": "test"}
    assert body["tlds"] == ["example", "test"]
    assert body["objects"] == ["domainName", "host", "contact"]


def test_discovery_advertises_nothing_the_proxy_does_not_do(client):
    body = client.get("/.well-known/rpp", headers=HEADERS).json()

    for member in ("extensions", "profiles", "links", "idnLgr", "notices"):
        assert member not in body


def test_discovery_datetime_is_utc_with_z(client):
    body = client.get("/.well-known/rpp", headers=HEADERS).json()

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", body["datetime"])


def test_discovery_has_no_cache_control(client):
    assert "Cache-Control" not in client.get("/.well-known/rpp", headers=HEADERS).headers


def test_discovery_base_url_does_not_come_from_the_host_header(client):
    body = client.get("/.well-known/rpp", headers={**HEADERS, "Host": "evil.example", "X-Forwarded-Host": "evil.example"}).json()

    assert body["versions"][0]["baseUrl"] == "https://rpp.example/rpp"


def test_discovery_without_rpp_cltrid_is_what_the_openapi_declares(client):
    response = client.get("/.well-known/rpp", headers={"Accept": MEDIA_TYPE})

    assert response.status_code == 400
    assert response.headers["Content-Type"].startswith("application/problem+json")


MISSING = [
    ("rpp_base_url", None), ("rpp_tlds", None), ("rpp_tlds", []),
    ("rpp_environment_name", None), ("rpp_environment_status", None),
]


@pytest.mark.parametrize("key, value", MISSING)
def test_missing_configuration_is_a_500_that_names_nothing(key, value, caplog):
    settings = SimpleNamespace(**{**vars(SETTINGS), key: value})

    with caplog.at_level(logging.WARNING):
        response = app_with(settings).get("/.well-known/rpp", headers=HEADERS)

    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
    assert "rpp_" not in response.text
    assert key in caplog.text


def test_no_settings_at_all_is_a_500():
    response = create_app(NoEppAuthenticator()).test_client().get("/.well-known/rpp", headers=HEADERS)

    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
