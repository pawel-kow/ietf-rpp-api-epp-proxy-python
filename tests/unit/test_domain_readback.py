import base64

import pytest

from app import create_app
from controller.epp_session_authenticator import EppSessionAuthenticator
from tests.helper.fake_epp_client import FakeEppClient

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'


def epp_reply(code, msg, res_data="", cl_trid=""):
    cl_trid_element = f"<clTRID>{cl_trid}</clTRID>" if cl_trid else ""
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>{msg}</msg></result>{res_data}'
        f'<trID>{cl_trid_element}<svTRID>sv-1</svTRID></trID>'
        '</response></epp>'
    )


UPDATED = (True, "1000", epp_reply(1000, "Command completed successfully"))
CREATED = (True, "1000", epp_reply(
    1000,
    "Command completed successfully",
    f'<resData><domain:creData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
    '<domain:crDate>2026-11-04T10:00:00.0Z</domain:crDate></domain:creData></resData>',
))
INFO = (True, "1000", epp_reply(
    1000,
    "Command completed successfully",
    f'<resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
    '<domain:roid>D1-EX</domain:roid><domain:status s="ok"/><domain:clID>user</domain:clID>'
    '<domain:authInfo><domain:pw>Password1!@</domain:pw></domain:authInfo>'
    '</domain:infData></resData>',
))
INFO_FAILED = (False, "2400", epp_reply(2400, "Command failed"))

AUTH = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": "application/rpp+json",
    "Content-Type": "application/rpp+json",
    "RPP-Cltrid": "cl-1",
}
NEW_AUTH_INFO = {"@type": "authInfo", "method": "authinfo", "authdata": "NewPassword1!@"}
UPDATE_BODY = [{"op": "replace", "path": "/authInfo", "value": NEW_AUTH_INFO}]
CREATE_BODY = {
    "@type": "domainName",
    "name": "foo.example",
    "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "Password1!@"},
}


def client_with(replies):
    def factory(username, password):
        return FakeEppClient(username, password, replies=replies)

    return create_app(EppSessionAuthenticator(factory)).test_client()


def patch(http):
    return http.patch("/domainNames/foo.example", json=UPDATE_BODY, headers=AUTH)


def post(http):
    return http.post("/domainNames", json=CREATE_BODY, headers=AUTH)


def test_update_with_readback_is_a_200_with_the_domain():
    response = patch(client_with([UPDATED, INFO]))

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json()["name"] == "FOO.EXAMPLE"


def test_create_with_readback_is_a_201_with_the_domain():
    response = post(client_with([CREATED, INFO]))

    assert response.status_code == 201
    assert response.headers["RPP-Code"] == "01000"
    assert response.json()["name"] == "FOO.EXAMPLE"


@pytest.mark.parametrize("send, applied", [(patch, UPDATED), (post, CREATED)])
@pytest.mark.parametrize("readback", [INFO_FAILED, ConnectionError("backend gone")])
def test_failed_readback_after_a_mutation_is_a_202(send, applied, readback):
    response = send(client_with([applied, readback]))

    assert response.status_code == 202
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.text == ""


def rpp_headers(response):
    return {k.lower(): v for k, v in response.headers.items() if k.lower().startswith("rpp-")}


CREATED_DATA = (
    f'<resData><domain:creData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
    '<domain:crDate>2026-11-04T10:00:00.0Z</domain:crDate></domain:creData></resData>'
)


@pytest.mark.parametrize("method, url, body, res_data", [
    ("patch", "/domainNames/foo.example", UPDATE_BODY, ""),
    ("post", "/domainNames", CREATE_BODY, CREATED_DATA),
])
@pytest.mark.parametrize("readback", [INFO_FAILED, ConnectionError("backend gone")])
def test_202_carries_the_same_rpp_headers_as_a_success(method, url, body, res_data, readback):
    applied = (True, "1000", epp_reply(1000, "Command completed successfully", res_data, cl_trid="cl-1"))
    def send(replies):
        return getattr(client_with(replies), method)(url, json=body, headers=AUTH)

    regular = send([applied, INFO])
    accepted = send([applied, readback])

    assert accepted.status_code == 202
    assert rpp_headers(accepted) == rpp_headers(regular)
    assert rpp_headers(accepted) == {
        "rpp-cltrid": "cl-1",
        "rpp-svtrid": "sv-1",
        "rpp-code": "01000",
    }
