import base64

import pytest

from app import create_app
from controller.epp_session_authenticator import EppSessionAuthenticator
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"
HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "rn32-cl-1",
}
BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}
PROCESSES = "/domainNames/foo.example/processes/renewProcesses"
BODY = {
    "@type": "renewProcess",
    "expiryDate": "2005-04-03T22:00:00.0Z",
    "renewalPeriod": {"@type": "period", "value": 5, "unit": "y"},
}
DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'


def epp_reply(code, res_data=""):
    return (
        f'<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="{code}"><msg>Message</msg></result>'
        f'{res_data}<trID><clTRID>rn32-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def renew_reply(code=1000, with_data=True):
    data = (
        f'<resData><domain:renData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
        '<domain:exDate>2010-04-03T22:00:00.0Z</domain:exDate></domain:renData></resData>'
    ) if with_data else ""
    return (True, str(code), epp_reply(code, data))


def info_reply(ex_date="2005-04-03T22:00:00.0Z"):
    return (True, "1000", epp_reply(1000, (
        f'<resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
        '<domain:roid>D1-EX</domain:roid><domain:status s="ok"/><domain:clID>user</domain:clID>'
        f'<domain:exDate>{ex_date}</domain:exDate></domain:infData></resData>'
    )))


def error_reply(code):
    return (False, str(code), epp_reply(code))


def setup(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, replies=list(replies)))
        return clients[-1]

    return create_app(EppSessionAuthenticator(factory)).test_client(), clients


def post(http, body=BODY):
    return http.post(PROCESSES, json=body, headers=BODY_HEADERS)


def test_renew_is_a_200_with_the_new_expiry_and_no_location():
    """Core §16.1.4: no persistent process resource, so 200 and not 201."""
    http, clients = setup(renew_reply())
    response = post(http)
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Cltrid"] == "rn32-cl-1"
    assert "Location" not in response.headers
    assert response.json() == {"@type": "renewProcess", "expiryDate": "2010-04-03T22:00:00.000000Z"}
    assert len(clients[-1].sent) == 1
    assert "<domain:curExpDate>2005-04-03</domain:curExpDate>" in clients[-1].sent[0]


def test_client_expiry_date_is_sent_without_a_read():
    http, clients = setup(renew_reply())
    post(http)
    assert len(clients[-1].sent) == 1
    assert "<info" not in clients[-1].sent[0]


def test_without_expiry_date_the_domain_is_read_first():
    http, clients = setup(info_reply(), renew_reply())
    response = post(http, {"@type": "renewProcess"})
    assert response.status_code == 200
    assert len(clients[-1].sent) == 2
    assert "info" in clients[-1].sent[0]
    assert "2005-04-03" in clients[-1].sent[1]
    assert "period" not in clients[-1].sent[1]


def test_read_error_is_passed_on_and_nothing_is_renewed():
    http, clients = setup(error_reply(2303))
    response = post(http, {"@type": "renewProcess"})
    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"
    assert len(clients[-1].sent) == 1


def test_pending_renew_is_a_200_with_01001():
    """Core §18.1 Table 10, spec-issues "Pending operations and 202"."""
    response = post(setup(renew_reply(1001, with_data=False))[0])
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01001"
    assert response.json() == {"@type": "renewProcess"}


def test_reply_without_ren_data_gives_the_type_only():
    response = post(setup(renew_reply(1000, with_data=False))[0])
    assert response.status_code == 200
    assert response.json() == {"@type": "renewProcess"}


@pytest.mark.parametrize("epp_code,status,rpp_code", [
    (2105, 409, "02105"),
    (2303, 404, "02303"),
    (2304, 409, "02304"),
    (2306, 422, "02306"),
    (2201, 403, "02201"),
])
def test_errors_are_passed_on(epp_code, status, rpp_code):
    """Core §18.1 Table 9."""
    response = post(setup(error_reply(epp_code))[0])
    assert response.status_code == status
    assert response.headers["RPP-Code"] == rpp_code
    assert response.headers["Content-Type"].startswith("application/problem+json")


@pytest.mark.parametrize("body", [
    {"@type": "renewProcess", "unknown": 1},
    {"@type": "renewProcess", "processId": "x"},
    {"@type": "renewProcess", "renewalPeriod": {"@type": "period", "value": 1, "unit": "y", "extra": 1}},
    {"@type": "renewProcess", "renewalPeriod": {"@type": "period", "value": 100, "unit": "y"}},
    {"@type": "renewProcess", "expiryDate": "not a date"},
    {"@type": "domainName"},
])
def test_invalid_body_is_a_400_without_epp(body):
    http, clients = setup()
    response = post(http, body)
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"
    assert not any(client.sent for client in clients)


def test_list_is_a_501():
    response = setup()[0].get(PROCESSES, headers=HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02101"
