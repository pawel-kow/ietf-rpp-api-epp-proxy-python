import logging
import re
import time
from datetime import datetime, timezone
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
    assert body["profiles"] == ["urn:ietf:params:rpp:profile:epp-compatibility"]


def test_discovery_advertises_nothing_the_proxy_does_not_do(client):
    body = client.get("/.well-known/rpp", headers=HEADERS).json()

    for member in ("extensions", "links", "idnLgr", "notices"):
        assert member not in body


def test_discovery_datetime_is_utc_with_z(client):
    body = client.get("/.well-known/rpp", headers=HEADERS).json()

    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", body["datetime"])


def test_discovery_datetime_is_the_current_time_whatever_the_local_zone(client, monkeypatch):
    monkeypatch.setenv("TZ", "Asia/Tokyo")
    time.tzset()
    try:
        body = client.get("/.well-known/rpp", headers=HEADERS).json()
    finally:
        monkeypatch.undo()
        time.tzset()

    sent = datetime.strptime(body["datetime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    assert abs((datetime.now(timezone.utc) - sent).total_seconds()) < 10


def test_discovery_has_no_cache_control(client):
    assert "Cache-Control" not in client.get("/.well-known/rpp", headers=HEADERS).headers


def test_discovery_base_url_does_not_come_from_the_host_header(client):
    body = client.get("/.well-known/rpp", headers={**HEADERS, "Host": "evil.example", "X-Forwarded-Host": "evil.example"}).json()

    assert body["versions"][0]["baseUrl"] == "https://rpp.example/rpp"


def test_discovery_without_rpp_cltrid_is_what_the_openapi_declares(client):
    response = client.get("/.well-known/rpp", headers={"Accept": MEDIA_TYPE})

    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert response.headers["Content-Type"].startswith("application/problem+json")


AUTHORIZATIONS = ["Basic !!!not-base64", "Basic Zm9vOmJhcg==", "Bearer abc.def", "Digest x", "garbage"]


@pytest.mark.parametrize("authorization", AUTHORIZATIONS)
def test_discovery_ignores_any_authorization(client, authorization):
    response = client.get("/.well-known/rpp", headers={**HEADERS, "Authorization": authorization})

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert FACTORY_CALLS == []


LEAK = "leak-marker-7f3a"
BAD = [
    ("rpp_base_url", None), ("rpp_base_url", ""), ("rpp_base_url", 5), ("rpp_base_url", {"a": LEAK}),
    ("rpp_base_url", [LEAK]), ("rpp_base_url", "not a url"), ("rpp_base_url", "/rpp"), ("rpp_base_url", "http://rpp.example"),
    ("rpp_base_url", "https://"), ("rpp_base_url", "https:///rpp"), ("rpp_base_url", "ftp://rpp.example"),
    ("rpp_tlds", None), ("rpp_tlds", []), ("rpp_tlds", "example"), ("rpp_tlds", 5), ("rpp_tlds", {"a": LEAK}),
    ("rpp_tlds", [""]), ("rpp_tlds", ["example", 5]), ("rpp_tlds", [["example"]]), ("rpp_tlds", [{"a": LEAK}]),
    ("rpp_environment_name", None), ("rpp_environment_name", ""), ("rpp_environment_name", 5),
    ("rpp_environment_name", {"a": LEAK}), ("rpp_environment_name", [LEAK]),
    ("rpp_environment_status", None), ("rpp_environment_status", ""), ("rpp_environment_status", 5),
    ("rpp_environment_status", {"a": LEAK}), ("rpp_environment_status", [LEAK]),
]


@pytest.mark.parametrize("key, value", BAD, ids=[f"{k}={v!r}" for k, v in BAD])
def test_bad_configuration_is_a_500_that_names_and_shows_nothing(key, value, caplog):
    settings = SimpleNamespace(**{**vars(SETTINGS), key: value})

    with caplog.at_level(logging.WARNING):
        response = app_with(settings).get("/.well-known/rpp", headers=HEADERS)

    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
    assert response.headers["Content-Type"].startswith("application/problem+json")
    assert response.json()["title"] == "Command failed"
    assert response.json()["detail"] == "The server is not configured to describe itself"
    assert "rpp_" not in response.text
    assert LEAK not in response.text
    assert key in caplog.text
    assert LEAK not in caplog.text
    assert [other for other in vars(SETTINGS) if other != key and other in caplog.text] == []


def test_no_settings_at_all_is_a_500():
    response = create_app(NoEppAuthenticator()).test_client().get("/.well-known/rpp", headers=HEADERS)

    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"


class BrokenSettings:
    @property
    def rpp_base_url(self):
        raise RuntimeError("boom")


def test_an_unexpected_failure_is_still_a_problem_detail_with_an_rpp_code():
    response = app_with(BrokenSettings()).get("/.well-known/rpp", headers=HEADERS)

    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
    assert response.headers["Content-Type"].startswith("application/problem+json")
