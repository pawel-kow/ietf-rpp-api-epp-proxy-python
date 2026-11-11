import base64

import pytest

from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.app import create_app
from core.session.session_pool import SessionPool
from tests.helper.epp_backends import epp_backends
from rpp.http.headers import rpp_code
from rpp.http.problem import http_status
from core.result.result_code import ResultCode
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

    return create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client()


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


def contact_check_reply(available, reason=""):
    return (True, "1000", epp_reply(1000, (
        '<resData><contact:chkData xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">'
        f'<contact:cd><contact:id avail="{int(available)}">JD-1234</contact:id>{reason}</contact:cd>'
        '</contact:chkData></resData>'
    )))


@pytest.mark.parametrize("available, status", [(True, 200), (False, 404)])
def test_contact_availability_get(available, status):
    response = client_with(contact_check_reply(available)).get("/contacts/JD-1234/availability", headers=HEADERS)

    assert response.status_code == status
    assert response.headers["Content-Type"] == MEDIA_TYPE
    assert response.headers["RPP-Code"] == "01000"
    assert response.json() == {"@type": "contactAvailability", "available": available}


def test_contact_availability_gives_the_reason():
    reply = contact_check_reply(False, "<contact:reason>In use</contact:reason>")

    response = client_with(reply).get("/contacts/JD-1234/availability", headers=HEADERS)

    assert response.json() == {"@type": "contactAvailability", "available": False, "reason": "In use"}


@pytest.mark.parametrize("available, status", [(True, 200), (False, 404)])
def test_contact_availability_head_has_the_status_of_get(available, status):
    response = client_with(contact_check_reply(available)).head("/contacts/JD-1234/availability", headers=HEADERS)

    assert response.status_code == status
    assert response.text == ""


def test_contact_availability_error_is_a_problem_detail():
    response = client_with((False, "2400", epp_reply(2400))).get("/contacts/JD-1234/availability", headers=HEADERS)

    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"


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
    body = {"@type": "domainName", "name": "foo.example", "status": [{"@type": "domainStatus", "label": "clientHold"}]}

    response = client_with().post("/domainNames", json=body, headers=BODY_HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


def test_dnssec_on_a_server_without_the_extension_is_a_501_unimplemented_extension():
    def factory(username, password):
        return FakeEppClient(username, password, extensions=())

    client = create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client()
    record = {
        "@type": "dnsRecord", "name": "@", "type": "ds",
        "rdata": {"keyTag": "1", "algorithm": "3", "digestType": "1", "digest": "AB"},
    }
    body = {"@type": "domainName", "name": "foo.example", "dns": {"@type": "dnsData", "records": [record]}}

    response = client.post("/domainNames", json=body, headers=BODY_HEADERS)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02103"
    assert response.json()["detail"] == (
        "DNSSEC needs urn:ietf:params:xml:ns:secDNS-1.1, which the EPP server does not offer"
    )


@pytest.mark.parametrize("method, url", [
    ("get", "/hosts/ns1.foo.example/processes/transferProcesses/latest"),
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
