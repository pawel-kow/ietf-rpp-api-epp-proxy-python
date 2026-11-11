import base64

import pytest

from eppclient.epp_profile import EPP_PROFILE
from app import create_app
from controller.session_authenticator import SessionAuthenticator
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

HOST_NS = 'xmlns:host="urn:ietf:params:xml:ns:host-1.0"'
NAME = "ns1.example.example"
AUTH = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": "application/rpp+json",
    "Content-Type": "application/rpp+json",
    "RPP-Cltrid": "cl-1",
}


def epp_reply(code, res_data=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def info(status="ok"):
    return (True, "1000", epp_reply(1000, (
        f'<resData><host:infData {HOST_NS}><host:name>NS1.EXAMPLE.EXAMPLE</host:name><host:roid>H1</host:roid>'
        f'<host:status s="{status}"/><host:addr ip="v4">192.0.2.1</host:addr><host:clID>foo</host:clID>'
        '<host:crID>foo</host:crID><host:crDate>2026-11-04T10:00:00.0Z</host:crDate></host:infData></resData>'
    )))


def check(avail, reason=""):
    return (True, "1000", epp_reply(1000, (
        f'<resData><host:chkData {HOST_NS}><host:cd><host:name avail="{avail}">{NAME}</host:name>{reason}'
        '</host:cd></host:chkData></resData>'
    )))


DONE = (True, "1000", epp_reply(1000))
PENDING = (True, "1001", epp_reply(1001))
CREATED = (True, "1000", epp_reply(1000, (
    f'<resData><host:creData {HOST_NS}><host:name>NS1.EXAMPLE.EXAMPLE</host:name>'
    '<host:crDate>2026-11-04T10:00:00.0Z</host:crDate></host:creData></resData>'
)))
OWN_NS = {"@type": "dnsRecord", "name": "@", "type": "ns", "rdata": {"nsdname": f"{NAME}."}}
CREATE_BODY = {"@type": "host", "hostName": NAME, "dns": {"@type": "dnsData", "records": [OWN_NS]}}
PATCH_BODY = [{"op": "add", "path": "/status", "value": {"@type": "hostStatus", "label": "clientUpdateProhibited"}}]


UNREADABLE = (True, "1000", info()[2].replace("<host:clID>foo</host:clID>", ""))


def error(code):
    return (False, str(code), epp_reply(code))


def client_with(*replies):
    def factory(username, password):
        return FakeEppClient(username, password, replies=replies)

    return create_app(SessionAuthenticator(epp_backends(factory)), EPP_PROFILE).test_client()


def post(http, body=CREATE_BODY):
    return http.post("/hosts", json=body, headers=AUTH)


def patch(http, body=PATCH_BODY):
    return http.patch(f"/hosts/{NAME}", json=body, headers=AUTH)


def put(http, body=CREATE_BODY):
    return http.put(f"/hosts/{NAME}", json=body, headers=AUTH)


def test_create_is_a_201_with_the_host_and_location():
    response = post(client_with(CREATED, info()))

    assert response.status_code == 201
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Cltrid"] == "cl-1"
    assert response.headers["Location"].endswith(f"/hosts/{NAME}")
    assert response.json()["hostName"] == "NS1.EXAMPLE.EXAMPLE"


def test_create_error_follows_table_9():
    response = post(client_with(error(2302)))

    assert response.status_code == 409
    assert response.headers["RPP-Code"] == "02302"


def test_unsupported_input_is_a_501():
    body = {**CREATE_BODY, "status": [{"@type": "hostStatus", "label": "clientUpdateProhibited"}]}

    response = post(client_with(), body)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


def test_invalid_input_is_a_400():
    record = {"@type": "dnsRecord", "name": "@", "type": "a", "rdata": {"address": "nope"}}

    response = post(client_with(), {**CREATE_BODY, "dns": {"@type": "dnsData", "records": [OWN_NS, record]}})

    assert response.status_code == 400


@pytest.mark.parametrize("send", [post, put])
def test_request_without_the_own_ns_record_is_a_400(send):
    response = send(client_with(), {"@type": "host", "hostName": NAME})

    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"


def test_removing_the_own_ns_record_is_a_501():
    response = patch(client_with(info()), [{"op": "remove", "path": "/dns/records", "match": {"type": "ns"}}])

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


def test_patch_adding_only_the_own_ns_record_is_refused_by_the_backend():
    response = patch(client_with(error(2003)), [{"op": "add", "path": "/dns/records", "value": OWN_NS}])

    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02003"


def test_read():
    response = client_with(info()).get(f"/hosts/{NAME}", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json()["dns"]["records"][1]["rdata"] == {"address": "192.0.2.1"}


def test_read_of_a_missing_host_is_a_404():
    response = client_with(error(2303)).get(f"/hosts/{NAME}", headers=AUTH)

    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"


def test_delete_is_a_200_without_a_body():
    response = client_with(DONE).delete(f"/hosts/{NAME}", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.text == ""


def test_pending_delete_reports_the_pending_code():
    response = client_with(PENDING).delete(f"/hosts/{NAME}", headers=AUTH)

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01001"


def test_delete_of_a_linked_host_is_a_409():
    response = client_with(error(2305)).delete(f"/hosts/{NAME}", headers=AUTH)

    assert response.status_code == 409
    assert response.headers["RPP-Code"] == "02305"


def test_delete_with_a_body_is_a_400():
    response = client_with(DONE).request("DELETE", f"/hosts/{NAME}", json={"a": 1}, headers=AUTH)

    assert response.status_code == 400


def test_availability_of_a_free_host():
    response = client_with(check(1)).get(f"/hosts/{NAME}/availability", headers=AUTH)

    assert response.status_code == 200
    assert response.json() == {"@type": "hostAvailability", "available": True}


def test_availability_of_a_taken_host_is_a_404():
    reason = "<host:reason>In use</host:reason>"

    response = client_with(check(0, reason)).get(f"/hosts/{NAME}/availability", headers=AUTH)

    assert response.status_code == 404
    assert response.json() == {"@type": "hostAvailability", "available": False, "reason": "In use"}


def test_head_availability():
    assert client_with(check(1)).head(f"/hosts/{NAME}/availability", headers=AUTH).status_code == 200
    assert client_with(check(0)).head(f"/hosts/{NAME}/availability", headers=AUTH).status_code == 404


def test_patch_is_a_200_with_the_host():
    response = patch(client_with(DONE, info()))

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json()["hostName"] == "NS1.EXAMPLE.EXAMPLE"


def test_put_is_a_200_with_the_host():
    response = put(client_with(info(), DONE, info()))

    assert response.status_code == 200
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.json()["hostName"] == "NS1.EXAMPLE.EXAMPLE"


def test_put_of_a_missing_host_is_a_404():
    response = put(client_with(error(2303)))

    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"


@pytest.mark.parametrize("send, replies", [
    (post, [CREATED]),
    (patch, [DONE]),
    (put, [info(), DONE]),
])
@pytest.mark.parametrize("readback", [error(2400), ConnectionError("backend gone"), UNREADABLE])
def test_failed_readback_after_a_mutation_is_a_202(send, replies, readback):
    response = send(client_with(*replies, readback))

    assert response.status_code == 202
    assert response.headers["RPP-Code"] == "01000"
    assert response.text == ""


def test_transfer_stays_unimplemented():
    response = client_with().get(f"/hosts/{NAME}/processes/transferProcesses/latest", headers=AUTH)

    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02101"
