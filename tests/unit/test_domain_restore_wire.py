import base64

import pytest

from app import create_app
from controller.session_authenticator import SessionAuthenticator
from tests.helper.epp_backends import epp_backends
from eppclient.eppclient import RGP_EXTENSION, SEC_DNS_EXTENSION
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"
HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "rs35-cl-1",
}
BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}
PROCESSES = "/domainNames/foo.example/processes/restoreProcesses"
LATEST = PROCESSES + "/latest"
DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'
RGP_NS = 'xmlns:rgp="urn:ietf:params:xml:ns:rgp-1.0"'
REPORT = {
    "@type": "restoreReport",
    "preData": "Pre-delete registration data.",
    "postData": "Post-restore registration data.",
    "deleteTime": "2025-01-10T12:00:00.0Z",
    "restoreTime": "2025-01-20T15:30:00.0Z",
    "restoreReason": "Domain deleted in error by client operator.",
    "statements": ["First statement.", "Second statement."],
}
UPDATE = {"@type": "restoreProcess", "restoreReport": REPORT}


def epp_reply(code, body=""):
    return (
        f'<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="{code}"><msg>Message</msg></result>'
        f'{body}<trID><clTRID>rs35-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def update_reply(code=1000, *statuses):
    inner = "".join(f'<rgp:rgpStatus s="{s}"/>' for s in statuses)
    extension = f"<extension><rgp:upData {RGP_NS}>{inner}</rgp:upData></extension>" if statuses else ""
    return (True, str(code), epp_reply(code, extension))


def info_reply(*statuses):
    inner = "".join(f'<rgp:rgpStatus s="{s}"/>' for s in statuses)
    return (True, "1000", epp_reply(1000, (
        f'<resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
        '<domain:roid>D1-EX</domain:roid><domain:status s="pendingDelete"/><domain:clID>user</domain:clID>'
        f'</domain:infData></resData><extension><rgp:infData {RGP_NS}>{inner}</rgp:infData></extension>'
    )))


def error_reply(code):
    return (False, str(code), epp_reply(code))


def setup(*replies, extensions=(SEC_DNS_EXTENSION, RGP_EXTENSION)):
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, replies=list(replies), extensions=extensions))
        return clients[-1]

    return create_app(SessionAuthenticator(epp_backends(factory))).test_client(), clients


def sent(clients):
    return [message for client in clients for message in client.sent]


# Create (core §16.9.3, json §8.1.13)

def test_request_is_a_200_without_location():
    """Core §16.1.4: EPP has no persistent process resource."""
    http, clients = setup(update_reply(1000, "pendingRestore"))
    response = http.post(PROCESSES, json={"@type": "restoreProcess"}, headers=BODY_HEADERS)
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Cltrid"] == "rs35-cl-1"
    assert "Location" not in response.headers
    assert response.json() == {"@type": "restoreProcess", "restoreStatus": "pendingRestore"}
    assert len(sent(clients)) == 1
    assert 'op="request"' in sent(clients)[0]


def test_request_without_up_data_is_pending_restore():
    http, _ = setup(update_reply(1000))
    response = http.post(PROCESSES, json={"@type": "restoreProcess"}, headers=BODY_HEADERS)
    assert response.json() == {"@type": "restoreProcess", "restoreStatus": "pendingRestore"}


def test_inline_report_is_a_501_without_epp():
    """RFC 3915 has no single-step restore, and it is not emulated."""
    http, clients = setup(update_reply())
    response = http.post(PROCESSES, json=UPDATE, headers=BODY_HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"
    assert not sent(clients)


@pytest.mark.parametrize("epp_code,status,rpp_code", [
    (2304, 409, "02304"),
    (2303, 404, "02303"),
    (2201, 403, "02201"),
])
def test_request_errors_are_passed_on(epp_code, status, rpp_code):
    """Core §16.9.3: not in redemptionPeriod is 409 02304."""
    http, _ = setup(error_reply(epp_code))
    response = http.post(PROCESSES, json={"@type": "restoreProcess"}, headers=BODY_HEADERS)
    assert response.status_code == status
    assert response.headers["RPP-Code"] == rpp_code


def test_server_without_rgp_is_a_501_without_epp():
    http, clients = setup(update_reply(), extensions=(SEC_DNS_EXTENSION,))
    response = http.post(PROCESSES, json={"@type": "restoreProcess"}, headers=BODY_HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02103"
    assert not sent(clients)


@pytest.mark.parametrize("body", [
    {"@type": "restoreProcess", "unknown": 1},
    {"@type": "restoreProcess", "processId": "x"},
    {"@type": "renewProcess"},
])
def test_invalid_create_is_a_400_without_epp(body):
    http, clients = setup()
    response = http.post(PROCESSES, json=body, headers=BODY_HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not sent(clients)


# Report (core §16.9.3, json §8.1.14)

def test_report_put_is_a_200_restored():
    http, clients = setup(update_reply(1000))
    response = http.put(LATEST, json=UPDATE, headers=BODY_HEADERS)
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert "Location" not in response.headers
    assert response.json() == {"@type": "restoreProcess", "restoreStatus": "restored"}
    assert len(sent(clients)) == 1
    assert 'op="report"' in sent(clients)[0]
    assert "Domain deleted in error by client operator." in sent(clients)[0]


def test_pending_report_is_a_200_pending_restore():
    http, _ = setup(update_reply(1001))
    response = http.put(LATEST, json=UPDATE, headers=BODY_HEADERS)
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01001"
    assert response.json() == {"@type": "restoreProcess", "restoreStatus": "pendingRestore"}


def test_report_patch():
    http, clients = setup(update_reply(1000))
    patch = [{"op": "add", "path": "/restoreReport", "value": REPORT}]
    response = http.patch(LATEST, json=patch, headers=BODY_HEADERS)
    assert response.status_code == 200
    assert response.json() == {"@type": "restoreProcess", "restoreStatus": "restored"}
    assert len(sent(clients)) == 1
    assert 'op="report"' in sent(clients)[0]


def test_report_not_in_pending_restore_is_a_409():
    """Core §16.9.3."""
    http, _ = setup(error_reply(2304))
    response = http.put(LATEST, json=UPDATE, headers=BODY_HEADERS)
    assert response.status_code == 409
    assert response.headers["RPP-Code"] == "02304"


@pytest.mark.parametrize("report", [
    {key: value for key, value in REPORT.items() if key != "preData"},
    {key: value for key, value in REPORT.items() if key != "restoreTime"},
    {**REPORT, "statements": ["Only one."]},
    {**REPORT, "deleteTime": "yesterday"},
])
def test_report_epp_cannot_take_is_a_400_without_epp(report):
    """RFC 3915 §4.2.5, json §6.2.10."""
    http, clients = setup()
    response = http.put(LATEST, json={**UPDATE, "restoreReport": report}, headers=BODY_HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not sent(clients)


def test_report_on_server_without_rgp_is_a_501():
    http, clients = setup(extensions=(SEC_DNS_EXTENSION,))
    response = http.put(LATEST, json=UPDATE, headers=BODY_HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02103"
    assert not sent(clients)


# Read (json §8.1.15)

@pytest.mark.parametrize("rgp,status", [
    ("pendingRestore", "pendingRestore"),
    ("pendingDelete", "rgpPendingDelete"),
])
def test_read(rgp, status):
    http, clients = setup(info_reply(rgp))
    response = http.get(LATEST, headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json() == {"@type": "restoreProcess", "restoreStatus": status}
    assert len(sent(clients)) == 1
    assert "<domain:info" in sent(clients)[0]


@pytest.mark.parametrize("rgp", [(), ("redemptionPeriod",), ("addPeriod",)])
def test_read_without_a_restore_is_a_404(rgp):
    """EPP cannot tell a restored domain from one never deleted, so `restored` is never read."""
    http, _ = setup(info_reply(*rgp))
    response = http.get(LATEST, headers=HEADERS)
    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"
    assert response.headers["RPP-Svtrid"] == "sv-1"


def test_read_of_unknown_domain_is_a_404():
    http, _ = setup(error_reply(2303))
    response = http.get(LATEST, headers=HEADERS)
    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"


def test_read_on_server_without_rgp_is_a_501():
    http, clients = setup(info_reply("pendingRestore"), extensions=(SEC_DNS_EXTENSION,))
    response = http.get(LATEST, headers=HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02103"
    assert not sent(clients)


# Not implemented: EPP has no process ids or history

@pytest.mark.parametrize("method,url", [
    ("get", PROCESSES),
    ("get", PROCESSES + "/abc"),
])
def test_list_and_process_id_are_501(method, url):
    http, clients = setup()
    response = getattr(http, method)(url, headers=HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02101"
