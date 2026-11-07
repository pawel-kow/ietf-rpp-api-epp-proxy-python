import base64

import pytest

from app import create_app
from controller.epp_session_authenticator import EppSessionAuthenticator
from tests.helper.fake_epp_client import FakeEppClient
from tests.unit.test_message_xml import DOMAIN, contact_trn, domain_trn, msg_q, pan, reply

MEDIA_TYPE = "application/rpp+json"
HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "msg-cl-1",
}
BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}
STATE = {"replies": [], "clients": []}


def factory(username, password):
    client = FakeEppClient(username, password)
    client.replies = STATE["replies"]  # the session is cached across requests, so the replies are shared
    STATE["clients"].append(client)
    return client


@pytest.fixture(scope="module")
def http():
    return create_app(EppSessionAuthenticator(factory)).test_client()


def answer(http, method, url, *replies, **kwargs):
    """Runs one request against an EPP backend that answers with the given replies."""
    STATE["replies"][:] = replies
    for client in STATE["clients"]:
        client.sent.clear()
    kwargs.setdefault("headers", HEADERS)
    return getattr(http, method)(url, **kwargs)


def ok(code, xml):
    return (True, str(code), xml)


def sent():
    return [message for client in STATE["clients"] for message in client.sent]


def head(res_data=None, text="Queue text.", id="42", count=3):
    return ok(1301, reply(1301, msg_q(text, count, id), res_data or domain_trn("pending")))


def test_query_returns_the_head_message(http):
    response = answer(http, "get", "/messages", head())
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01301"
    assert response.headers["RPP-Queue-Size"] == "3"
    assert response.headers["RPP-Cltrid"] == "msg-cl-1"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["Content-Language"] == "en-US"
    body = response.json()
    assert len(body) == 1
    assert body[0]["id"] == "42"
    assert body[0]["status"] == "queued"
    assert body[0]["data"]["@type"] == "transferRequestMessage"
    assert 'op="req"' in sent()[-1]


def test_query_on_an_empty_queue_is_an_empty_array(http):
    response = answer(http, "get", "/messages", ok(1300, reply(1300)))
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01300"
    assert response.json() == []
    assert response.headers["RPP-Queue-Size"] == "0"
    assert "Content-Language" not in response.headers


def test_query_ignores_the_type_parameter(http):
    response = answer(http, "get", "/messages?type=autoRenewalMessage", head())
    assert response.status_code == 200
    assert response.json()[0]["data"]["@type"] == "transferRequestMessage"


@pytest.mark.parametrize("res_data,data_type", [
    (domain_trn("serverApproved"), "transferOutcomeMessage"),
    (contact_trn("pending"), "transferRequestMessage"),
    (pan("domain", DOMAIN, "name", "1"), "reviewResponseMessage"),
    (None, "transferRequestMessage"),
])
def test_message_types(http, res_data, data_type):
    response = answer(http, "get", "/messages", head(res_data))
    assert response.json()[0]["data"]["@type"] == data_type


def test_message_without_structure_is_a_service_notice(http):
    xml = reply(1301, msg_q("Please note."))
    response = answer(http, "get", "/messages", ok(1301, xml))
    assert response.status_code == 200
    assert response.json()[0]["data"] == {"@type": "serviceNoticeMessage", "message": "Please note."}


def test_unknown_res_data_is_a_notice_that_can_be_acked(http):
    res = '<resData><x:other xmlns:x="urn:example:x"/></resData>'
    response = answer(http, "get", "/messages", ok(1301, reply(1301, msg_q("Odd."), res)))
    assert response.status_code == 200
    data = response.json()[0]["data"]
    assert data["@type"] == "serviceNoticeMessage"
    assert "urn:example:x" in data["message"]
    ack = answer(http, "delete", "/messages/42", ok(1000, reply(1000, '<msgQ count="0" id="42"/>')))
    assert ack.status_code == 200


def test_message_that_fails_validation_is_a_notice_and_not_a_500(http):
    res = domain_trn("pending").replace(">pending<", ">weird<")
    response = answer(http, "get", "/messages", head(res))
    assert response.status_code == 200
    assert response.json()[0]["data"]["@type"] == "serviceNoticeMessage"


def test_message_with_a_bad_date_is_not_a_500(http):
    xml = reply(1301, '<msgQ count="1" id="9"><msg>Hi</msg></msgQ>')
    response = answer(http, "get", "/messages", ok(1301, xml))
    assert response.status_code == 200
    assert response.json()[0]["creationDate"]


def test_epp_error_on_query(http):
    response = answer(http, "get", "/messages", (False, "2400", reply(2400)))
    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"


def test_read_of_the_head(http):
    response = answer(http, "get", "/messages/42", head())
    assert response.status_code == 200
    assert response.headers["RPP-Queue-Size"] == "3"
    assert response.json()["id"] == "42"
    assert 'op="req"' in sent()[-1]


def test_read_of_another_id_is_a_501(http):
    response = answer(http, "get", "/messages/43", head())
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"
    assert len(sent()) == 1


def test_read_on_an_empty_queue_is_a_404(http):
    response = answer(http, "get", "/messages/42", ok(1300, reply(1300)))
    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"


def test_ack_sends_the_id_and_has_no_content(http):
    response = answer(http, "delete", "/messages/42", ok(1000, reply(1000, '<msgQ count="2" id="43"/>')))
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Queue-Size"] == "2"
    assert response.headers["RPP-Cltrid"] == "msg-cl-1"
    assert response.content == b""
    assert 'op="ack"' in sent()[-1] and 'msgID="42"' in sent()[-1]


def test_ack_that_empties_the_queue(http):
    response = answer(http, "delete", "/messages/42", ok(1000, reply(1000, '<msgQ count="0"/>')))
    assert response.headers["RPP-Queue-Size"] == "0"


def test_ack_of_an_unknown_id_is_a_404(http):
    response = answer(http, "delete", "/messages/99", (False, "2303", reply(2303)))
    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"
    assert response.headers["Content-Type"].startswith("application/problem+json")


def test_ack_with_content_is_a_400_without_epp(http):
    answer(http, "get", "/messages", head())  # resets what was sent
    STATE["clients"][0].sent.clear()
    response = http.request("DELETE", "/messages/42", data=b'{"a":1}', headers=BODY_HEADERS)
    assert response.status_code == 400
    assert sent() == []


def test_create_is_a_501_and_names_no_internals(http):
    body = {"@type": "message", "data": {"@type": "serviceNoticeMessage", "message": "x"}}
    response = answer(http, "post", "/messages", json=body, headers=BODY_HEADERS)
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02101"
    assert "controller" not in response.text
    assert sent() == []


def test_create_with_an_invalid_body_is_a_400(http):
    response = answer(http, "post", "/messages", json={"@type": "message"}, headers=BODY_HEADERS)
    assert response.status_code == 400

