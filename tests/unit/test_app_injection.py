import base64


from app import create_app
from controller.epp_session_authenticator import EppSessionAuthenticator
from tests.helper.fake_epp_client import FakeEppClient

OBJECT_DOES_NOT_EXIST = (
    '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
    '<result code="2303"><msg>Object does not exist</msg></result>'
    '<trID><svTRID>sv-1</svTRID></trID>'
    '</response></epp>'
)


def auth_header(username, password):
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def client_for(**fake_options):
    created = []

    def factory(username, password):
        client = FakeEppClient(username, password, **fake_options)
        created.append(client)
        return client

    return create_app(EppSessionAuthenticator(factory)).test_client(), created


def test_request_is_served_by_the_injected_client():
    http, created = client_for(reply=(False, "2303", OBJECT_DOES_NOT_EXIST))

    response = http.delete("/domains/missing.example", headers=auth_header("user", "pw"))

    assert response.status_code == 404
    assert response.headers["RPP-code"] == "2303"
    assert "missing.example" in created[0].sent[0]


def test_unreachable_backend_is_a_401():
    http, _ = client_for(reachable=False)

    response = http.delete("/domains/any.example", headers=auth_header("user", "pw"))

    assert response.status_code == 401


def test_missing_credentials_do_not_reach_the_factory():
    http, created = client_for()

    response = http.delete("/domains/any.example")

    assert response.status_code == 401
    assert created == []
