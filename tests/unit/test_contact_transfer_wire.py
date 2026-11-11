import base64

import pytest

from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.app import create_app
from core.session.session_pool import SessionPool
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"
HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "cl-1",
}
BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}
PROCESSES = "/contacts/FO-1/processes/transferProcesses"
LATEST = f"{PROCESSES}/latest"
CREATE_BODY = {"@type": "transferProcess", "transferDir": "pull"}
TYPE_ONLY = {"@type": "transferProcess"}


def epp_reply(code, res_data=""):
    return (
        f'<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="{code}"><msg>Message</msg></result>'
        f'{res_data}<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def transfer_reply(code, status):
    return (True, str(code), epp_reply(code, (
        '<resData><contact:trnData xmlns:contact="urn:ietf:params:xml:ns:contact-1.0">'
        f'<contact:id>FO-1</contact:id><contact:trStatus>{status}</contact:trStatus>'
        '<contact:reID>ClientX</contact:reID><contact:reDate>2000-06-08T22:00:00.0Z</contact:reDate>'
        '<contact:acID>ClientY</contact:acID><contact:acDate>2000-06-13T22:00:00.0Z</contact:acDate>'
        '</contact:trnData></resData>'
    )))


def error_reply(code):
    return (False, str(code), epp_reply(code))


def setup(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, replies=list(replies)))
        return clients[-1]

    return create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client(), clients


def client_with(*replies):
    return setup(*replies)[0]


def post_create(http, **kwargs):
    return http.post(PROCESSES, json=CREATE_BODY, headers=BODY_HEADERS, **kwargs)


def test_pending_request_is_created_at_latest():
    """Core §16.9.5.1."""
    response = post_create(client_with(transfer_reply(1001, "pending")))
    assert response.status_code == 201
    assert response.headers["RPP-Code"] == "01001"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Cltrid"] == "cl-1"
    assert response.headers["Location"].endswith(LATEST)
    assert response.json()["trStatus"] == "pending"
    assert response.json()["@type"] == "transferProcess"


def test_request_completed_at_once_exposes_no_process():
    """Core §16.1.4: without a persistent process resource, 200 and not 201."""
    response = post_create(client_with(transfer_reply(1000, "serverApproved")))
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert "Location" not in response.headers
    assert response.json()["trStatus"] == "serverApproved"


def test_authorization_header_reaches_epp():
    http, clients = setup(transfer_reply(1001, "pending"))
    headers = {**BODY_HEADERS, "RPP-Authorization": "authinfo value=TXkgU2VjcmV0IFRva2Vu, roid=REG-123"}
    assert http.post(PROCESSES, json=CREATE_BODY, headers=headers).status_code == 201
    assert "My Secret Token" in clients[-1].sent[-1]
    assert 'roid="REG-123"' in clients[-1].sent[-1]


def test_malformed_authorization_is_a_400_without_epp():
    http, clients = setup()
    headers = {**BODY_HEADERS, "RPP-Authorization": "authinfo value=%%%"}
    response = http.post(PROCESSES, json=CREATE_BODY, headers=headers)
    assert response.status_code == 400
    assert "%%%" not in response.text
    assert not any("transfer" in sent for client in clients for sent in client.sent)


def test_other_authorization_method_is_a_501():
    headers = {**BODY_HEADERS, "RPP-Authorization": "bearer abc"}
    response = client_with().post(PROCESSES, json=CREATE_BODY, headers=headers)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


def test_push_is_a_501():
    body = {"@type": "transferProcess", "transferDir": "push", "gainingClientId": "ClientX"}
    response = client_with().post(PROCESSES, json=body, headers=BODY_HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


def test_query():
    response = client_with(transfer_reply(1000, "pending")).get(LATEST, headers=HEADERS)
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json()["transferDir"] == "pull"


def test_query_sends_the_query_operation():
    http, clients = setup(transfer_reply(1000, "pending"))
    http.get(LATEST, headers=HEADERS)
    assert 'op="query"' in clients[-1].sent[-1]


def test_cancel():
    http, clients = setup(transfer_reply(1000, "clientCancelled"))
    response = http.delete(LATEST, headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["trStatus"] == "clientCancelled"
    assert 'op="cancel"' in clients[-1].sent[-1]


def test_cancel_takes_no_body():
    """Core §16.1.4."""
    response = client_with().request("DELETE", LATEST, json=TYPE_ONLY, headers=BODY_HEADERS)
    assert response.status_code == 400


def test_approve_without_a_body():
    """Core §16.9.5.5."""
    http, clients = setup(transfer_reply(1000, "clientApproved"))
    response = http.post(f"{LATEST}/transferApprove", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["trStatus"] == "clientApproved"
    assert 'op="approve"' in clients[-1].sent[-1]


def test_approve_with_the_type_only_body():
    """Json §8.1.10."""
    http, clients = setup(transfer_reply(1000, "clientApproved"))
    response = http.post(f"{LATEST}/transferApprove", json=TYPE_ONLY, headers=BODY_HEADERS)
    assert response.status_code == 200
    assert 'op="approve"' in clients[-1].sent[-1]


def test_reject_without_a_body():
    """Core §16.9.5.4."""
    http, clients = setup(transfer_reply(1000, "clientRejected"))
    response = http.post(f"{LATEST}/transferReject", headers=HEADERS)
    assert response.status_code == 200
    assert response.json()["trStatus"] == "clientRejected"
    assert 'op="reject"' in clients[-1].sent[-1]


def test_reject_with_the_type_only_body():
    http = client_with(transfer_reply(1000, "clientRejected"))
    response = http.post(f"{LATEST}/transferReject", json=TYPE_ONLY, headers=BODY_HEADERS)
    assert response.status_code == 200


def test_reject_with_reason_is_a_501():
    """Data-objects §10.1.1.5: not in the EPP Compatibility Profile."""
    body = {**TYPE_ONLY, "reason": "No"}
    response = client_with().post(f"{LATEST}/transferReject", json=body, headers=BODY_HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"


@pytest.mark.parametrize("epp_code,status,rpp_code", [
    (2106, 409, "02106"),
    (2201, 403, "02201"),
    (2202, 401, "02202"),
    (2300, 409, "02300"),
    (2303, 404, "02303"),
])
def test_request_errors(epp_code, status, rpp_code):
    """Core §18.1 Table 9."""
    response = post_create(client_with(error_reply(epp_code)))
    assert response.status_code == status
    assert response.headers["RPP-Code"] == rpp_code
    assert response.headers["Content-Type"].startswith("application/problem+json")


@pytest.mark.parametrize("method,url", [
    ("GET", LATEST),
    ("DELETE", LATEST),
    ("POST", f"{LATEST}/transferApprove"),
    ("POST", f"{LATEST}/transferReject"),
])
def test_nothing_pending_is_a_409(method, url):
    response = client_with(error_reply(2301)).request(method, url, headers=HEADERS)
    assert response.status_code == 409
    assert response.headers["RPP-Code"] == "02301"


@pytest.mark.parametrize("method,url", [
    ("GET", PROCESSES),
    ("GET", f"{PROCESSES}/XYZ-12345"),
    ("DELETE", f"{PROCESSES}/XYZ-12345"),
    ("POST", f"{PROCESSES}/XYZ-12345/transferApprove"),
    ("POST", f"{PROCESSES}/XYZ-12345/transferReject"),
])
def test_what_needs_process_ids_is_a_501(method, url):
    response = client_with().request(method, url, headers=HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02101"


def test_period_is_a_400():
    """Json §4.4: a contact transfer has no period."""
    body = {**CREATE_BODY, "transferPeriod": {"@type": "period", "value": 1, "unit": "y"}}
    http, clients = setup()
    response = http.post(PROCESSES, json=body, headers=BODY_HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not any("transfer" in sent for client in clients for sent in client.sent)


def test_unknown_member_of_a_reject_is_a_400():
    body = {**TYPE_ONLY, "unknown": 1}
    response = client_with().post(f"{LATEST}/transferReject", json=body, headers=BODY_HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"


def approve(http, **kwargs):
    return http.post(f"{LATEST}/transferApprove", headers=BODY_HEADERS, **kwargs)


@pytest.mark.parametrize("body", [
    {"x": 1},
    {"@type": "nonsense"},
    {},
    [],
    "text",
    {**TYPE_ONLY, "unknown": 1},
])
def test_approve_with_an_invalid_body_is_a_400_without_epp(body):
    """Approve cannot be undone, so nothing is sent for a body the schema does not allow. Json §4.4."""
    http, clients = setup()
    response = approve(http, json=body)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not any("transfer" in sent for client in clients for sent in client.sent)


@pytest.mark.parametrize("content_type,data", [(MEDIA_TYPE, "{not json"), ("text/plain", "hello")])
def test_approve_with_a_body_that_is_not_json_is_a_400_without_epp(content_type, data):
    http, clients = setup()
    response = http.post(f"{LATEST}/transferApprove", data=data, headers={**HEADERS, "Content-Type": content_type})
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not any("transfer" in sent for client in clients for sent in client.sent)


def test_approve_with_a_reason_is_a_501_without_epp():
    """Data-objects §10.1.1.5: not in the EPP Compatibility Profile."""
    http, clients = setup()
    response = approve(http, json={**TYPE_ONLY, "reason": "ok"})
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"
    assert not any("transfer" in sent for client in clients for sent in client.sent)


def test_create_with_a_read_only_member_is_a_400_without_epp():
    """Json §4.4: a server MUST reject members that are not writable."""
    for member in ("trStatus", "reqClientId", "actClientId", "requestDate", "actionDate", "processId"):
        http, clients = setup()
        response = http.post(
            PROCESSES, json={**CREATE_BODY, member: "pending"}, headers=BODY_HEADERS)
        assert response.status_code == 400, member
        assert response.headers["RPP-Code"] == "02001"
        assert not any("transfer" in sent for client in clients for sent in client.sent)


@pytest.mark.parametrize("method,url", [
    ("POST", PROCESSES),
    ("DELETE", LATEST),
    ("POST", f"{LATEST}/transferApprove"),
    ("POST", f"{LATEST}/transferReject"),
])
def test_mutation_without_trn_data_is_a_202_without_body(method, url):
    """The transfer was applied, but EPP gave no state to show."""
    no_data = (True, "1000", epp_reply(1000))
    kwargs = {"json": CREATE_BODY} if url == PROCESSES else {}
    response = client_with(no_data).request(method, url, headers=BODY_HEADERS if kwargs else HEADERS, **kwargs)
    assert response.status_code == 202
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.content == b""


FOUR = [
    ("GET", LATEST, "query", "clientApproved"),
    ("DELETE", LATEST, "cancel", "clientCancelled"),
    ("POST", f"{LATEST}/transferApprove", "approve", "clientApproved"),
    ("POST", f"{LATEST}/transferReject", "reject", "clientRejected"),
]


@pytest.mark.parametrize("method,url,op,status", FOUR)
def test_authorization_header_reaches_epp_on_every_operation(method, url, op, status):
    http, clients = setup(transfer_reply(1000, status))
    headers = {**HEADERS, "RPP-Authorization": "authinfo value=TXkgU2VjcmV0IFRva2Vu, roid=REG-123"}
    assert http.request(method, url, headers=headers).status_code == 200
    assert f'op="{op}"' in clients[-1].sent[-1]
    assert "My Secret Token" in clients[-1].sent[-1]
    assert 'roid="REG-123"' in clients[-1].sent[-1]


@pytest.mark.parametrize("method,url,op,status", FOUR)
def test_malformed_authorization_is_a_400_without_epp_on_every_operation(method, url, op, status):
    http, clients = setup(transfer_reply(1000, status))
    response = http.request(method, url, headers={**HEADERS, "RPP-Authorization": "authinfo value=%%%"})
    assert response.status_code == 400
    assert not any("transfer" in sent for client in clients for sent in client.sent)


@pytest.mark.parametrize("method,url,op,status", FOUR)
def test_other_authorization_method_is_a_501_without_epp_on_every_operation(method, url, op, status):
    http, clients = setup(transfer_reply(1000, status))
    response = http.request(method, url, headers={**HEADERS, "RPP-Authorization": "bearer abc"})
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"
    assert not any("transfer" in sent for client in clients for sent in client.sent)


def test_query_without_trn_data_is_a_500_with_a_clean_detail():
    """A query applied nothing, so there is nothing to confirm."""
    response = client_with((True, "1000", epp_reply(1000))).get(LATEST, headers=HEADERS)
    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert "Error" not in response.json()["detail"] and "object" not in response.json()["detail"]


@pytest.mark.parametrize("data", [b"null", b" ", b"\n"])
def test_approve_with_a_body_of_null_or_whitespace_is_a_400_without_epp(data):
    """Bytes are content, even when they parse to nothing."""
    http, clients = setup()
    response = http.post(f"{LATEST}/transferApprove", content=data, headers=BODY_HEADERS)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not any("transfer" in sent for client in clients for sent in client.sent)
