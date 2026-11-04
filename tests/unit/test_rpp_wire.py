import base64

import pytest

from app import create_app
from controller.epp_session_authenticator import EppSessionAuthenticator
from controller.helper.rpp_response import http_status, rpp_code
from models import ResultCode
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"
HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "cl-1",
}
BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}


def epp_reply(code, res_data=""):
    return (
        f'<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="{code}"><msg>Message</msg></result>'
        f'{res_data}<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def check_reply(available):
    return (True, "1000", epp_reply(1000, (
        '<resData><domain:chkData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">'
        f'<domain:cd><domain:name avail="{int(available)}">foo.example</domain:name></domain:cd>'
        '</domain:chkData></resData>'
    )))


def client_with(*replies):
    def factory(username, password):
        return FakeEppClient(username, password, replies=list(replies))

    return create_app(EppSessionAuthenticator(factory)).test_client()


@pytest.mark.parametrize("available, status", [(True, 200), (False, 404)])
def test_availability_get(available, status):
    response = client_with(check_reply(available)).get("/domainNames/foo.example/availability", headers=HEADERS)

    assert response.status_code == status
    assert response.headers["Content-Type"] == MEDIA_TYPE
    assert response.json() == {"@type": "domainNameAvailability", "available": available}


@pytest.mark.parametrize("available, status", [(True, 200), (False, 404)])
def test_availability_head_has_the_status_of_get(available, status):
    response = client_with(check_reply(available)).head("/domainNames/foo.example/availability", headers=HEADERS)

    assert response.status_code == status
    assert response.text == ""


@pytest.mark.parametrize("epp_code, rpp_result", [(1000, "01000"), (1001, "01001")])
def test_delete_is_a_200_without_content(epp_code, rpp_result):
    reply = (True, str(epp_code), epp_reply(epp_code))

    response = client_with(reply).delete("/domainNames/foo.example", headers=HEADERS)

    assert response.status_code == 200
    assert response.text == ""
    assert response.headers["RPP-Code"] == rpp_result


def test_error_is_a_problem_detail():
    reply = (False, "2303", epp_reply(2303))

    response = client_with(reply).get("/domainNames/foo.example", headers=HEADERS)

    assert response.status_code == 404
    assert response.headers["Content-Type"] == "application/problem+json"
    assert response.headers["RPP-Code"] == "02303"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Cltrid"] == "cl-1"
    body = response.json()
    assert body["type"] == "urn:ietf:params:rpp:error"
    assert body["status"] == 404
    assert body["errors"] == [{"type": "urn:ietf:params:rpp:error", "result": "02303", "reason": "Message"}]


def test_unsupported_input_is_a_501_unimplemented_option():
    body = {"@type": "domainName", "name": "foo.example", "dns": {"@type": "dnsData"}}

    response = client_with().post("/domainNames", json=body, headers=BODY_HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


@pytest.mark.parametrize("method, url", [
    ("get", "/hosts/ns1.foo.example/processes/transferProcesses/latest"),
    ("put", "/domainNames/foo.example"),
    ("get", "/contacts/JD-1234/availability"),
    ("get", "/.well-known/rpp"),
])
def test_unimplemented_operation_is_a_501_unimplemented_command(method, url):
    response = getattr(client_with(), method)(url, headers=HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02101"
    assert response.headers["RPP-Svtrid"]


def test_mapper_validation_error_does_not_echo_the_request():
    operation = {"op": "replace", "path": "/authInfo", "value": {"pw": "Secret1!"}}

    response = client_with().patch("/domainNames/foo.example", json=[operation], headers=BODY_HEADERS)

    assert response.status_code == 400
    assert "Secret1!" not in response.text


def test_missing_client_transaction_id_is_a_400():
    headers = {k: v for k, v in HEADERS.items() if k != "RPP-Cltrid"}

    response = client_with().get("/domainNames/foo.example", headers=headers)

    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"


def test_create_answers_with_the_location():
    created = (True, "1000", epp_reply(1000, (
        '<resData><domain:creData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">'
        '<domain:name>foo.example</domain:name><domain:crDate>2026-01-01T00:00:00.0Z</domain:crDate>'
        '</domain:creData></resData>'
    )))
    info = (True, "1000", epp_reply(1000, (
        '<resData><domain:infData xmlns:domain="urn:ietf:params:xml:ns:domain-1.0">'
        '<domain:name>foo.example</domain:name><domain:roid>D-1</domain:roid>'
        '<domain:status s="ok"/><domain:clID>user</domain:clID></domain:infData></resData>'
    )))

    response = client_with(created, info).post(
        "/domainNames", json={"@type": "domainName", "name": "foo.example"}, headers=BODY_HEADERS,
    )

    assert response.status_code == 201
    assert response.headers["Location"].endswith("/domainNames/foo.example")


@pytest.mark.parametrize("code, status", [
    (ResultCode.OBJECT_EXISTS, 409),
    (ResultCode.OBJECT_DOES_NOT_EXIST, 404),
    (ResultCode.OBJECT_ASSOCIATION_PROHIBITS_OPERATION, 409),
    (ResultCode.AUTHORIZATION_ERROR, 403),
    (ResultCode.BILLING_FAILURE, 402),
    (ResultCode.PARAMETER_VALUE_POLICY_ERROR, 422),
    (ResultCode.REQUIRED_PARAMETER_MISSING, 400),
    (ResultCode.COMMAND_FAILED, 500),
])
def test_status_mapping_follows_core_tables_9_and_10(code, status):
    assert http_status(code) == status


def test_epp_codes_get_the_leading_zero():
    assert rpp_code(ResultCode.OBJECT_EXISTS) == "02302"
