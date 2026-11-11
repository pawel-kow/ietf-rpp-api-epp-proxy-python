import base64


from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.app import create_app
from core.session.session_pool import SessionPool
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

OBJECT_DOES_NOT_EXIST = (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
    '<result code="2303"><msg>Object does not exist</msg></result>'
    '<trID><svTRID>sv-1</svTRID></trID>'
    '</response></epp>'
)


def auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}", "Accept": "application/rpp+json", "RPP-Cltrid": "cl-1"}


def client_for(**fake_options):
    created = []

    def factory(username, password):
        client = FakeEppClient(username, password, **fake_options)
        created.append(client)
        return client

    return create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client(), created


def test_request_is_served_by_the_injected_client():
    http, created = client_for(reply=(False, "2303", OBJECT_DOES_NOT_EXIST))

    response = http.delete("/domainNames/missing.example", headers=auth_header("user", "pw"))

    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"
    assert "missing.example" in created[0].sent[0]


def test_unreachable_backend_is_a_401():
    http, _ = client_for(reachable=False)

    response = http.delete("/domainNames/any.example", headers=auth_header("user", "pw"))

    assert response.status_code == 401


def test_missing_credentials_do_not_reach_the_factory():
    http, created = client_for()

    response = http.delete("/domainNames/any.example")

    assert response.status_code == 401
    assert created == []
