import base64

import pytest
from connexion import ProblemException

from core.result.result_code import ResultCode
from core.session.session_pool import SessionPool
from registry_adapter.epp.profile import EPP_PROFILE
from rpp.handlers.message.message_handlers import _require_valid_id
from rpp.http.app import create_app
from rpp.http.headers import problem_headers
from tests.helper.captured_log import capture_log
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient
from tests.unit.test_message_xml import contact_trn, DOMAIN, domain_trn, msg_q, pan, reply

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
    return create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client()


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
    """A pending-action reply without a svTRID parses, and fails the schema, which requires serverTransactionId."""
    res = pan("domain", DOMAIN, "name", "1").replace("<svTRID>sv-9</svTRID>", "")
    with capture_log() as caplog:
        response = answer(http, "get", "/messages", head(res))
    assert response.status_code == 200
    data = response.json()[0]["data"]
    assert data["@type"] == "serviceNoticeMessage"
    assert "panData" in data["message"]
    assert "panData" in caplog.text


@pytest.mark.parametrize("bad", ["garbage", "2026-13-45T00:00:00Z", "2026-01-01T23:59:60Z", "", "2026-01-01T24:00:00Z"])
def test_message_with_a_bad_date_is_not_a_500(http, bad):
    xml = reply(1301, f'<msgQ count="1" id="9"><qDate>{bad}</qDate><msg>Hi</msg></msgQ>')
    response = answer(http, "get", "/messages", ok(1301, xml))
    assert response.status_code == 200
    assert response.json()[0]["creationDate"]


def test_message_without_a_date_is_not_a_500(http):
    xml = reply(1301, '<msgQ count="1" id="9"><msg>Hi</msg></msgQ>')
    response = answer(http, "get", "/messages", ok(1301, xml))
    assert response.status_code == 200
    assert response.json()[0]["creationDate"]


@pytest.mark.parametrize("res_data", [
    domain_trn("pending").replace("</domain:trnData>", "<domain:extra>x</domain:extra></domain:trnData>"),
    '<resData><other xmlns="">x</other></resData>',
])
def test_reply_that_does_not_follow_the_schema_can_be_read_and_acked(http, res_data):
    response = answer(http, "get", "/messages", head(res_data))
    assert response.status_code == 200
    assert response.json()[0]["id"] == "42"
    assert response.json()[0]["data"]["@type"] == "serviceNoticeMessage"
    assert response.headers["RPP-Queue-Size"] == "3"
    ack = answer(http, "delete", "/messages/42", ok(1000, reply(1000, '<msgQ count="2" id="43"/>')))
    assert ack.status_code == 200


@pytest.mark.parametrize("lang", ["日本", "a&#13;&#10;b: c", "en us", "-en", ""])
def test_a_language_that_is_no_tag_is_not_sent(http, lang):
    xml = reply(1301, f'<msgQ count="1" id="9"><qDate>2026-11-05T16:49:34.0Z</qDate><msg lang="{lang}">Hi</msg></msgQ>')
    response = answer(http, "get", "/messages", ok(1301, xml))
    assert response.status_code == 200
    assert "Content-Language" not in response.headers
    assert response.headers["RPP-Code"] == "01301"


def test_language_defaults_to_en_as_in_epp(http):
    xml = reply(1301, '<msgQ count="1" id="9"><qDate>2026-11-05T16:49:34.0Z</qDate><msg>Hi</msg></msgQ>')
    assert answer(http, "get", "/messages", ok(1301, xml)).headers["Content-Language"] == "en"


@pytest.mark.parametrize("count", ["-1", "many"])
def test_queue_size_is_sent_only_as_an_integer_of_at_least_0(http, count):
    xml = reply(1301, f'<msgQ count="{count}" id="9"><qDate>2026-11-05T16:49:34.0Z</qDate><msg>Hi</msg></msgQ>')
    response = answer(http, "get", "/messages", ok(1301, xml))
    assert response.status_code == 200
    assert "RPP-Queue-Size" not in response.headers


def test_1301_without_a_message_id_is_a_500_and_not_an_empty_queue(http):
    response = answer(http, "get", "/messages", ok(1301, reply(1301)))
    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.json()["detail"] == "The reply of the EPP server cannot be read, so the message cannot be acknowledged"


@pytest.mark.parametrize("code,status", [("2309", 400), ("2409", 500), ("2105", 409)])
def test_an_error_code_not_in_table_9_uses_table_10_and_keeps_the_reply(http, code, status):
    """Core §18.1: Table 10 maps by class, and RPP-Code is the EPP code with a leading 0."""
    response = answer(http, "get", "/messages", (False, code, reply(code, msg="Odd failure")))
    assert response.status_code == status
    assert response.headers["RPP-Code"] == "0" + code
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.json()["detail"] == "Odd failure"


def test_an_unknown_success_code_is_200_with_its_own_code(http):
    response = answer(http, "get", "/messages", ok(1302, reply(1302, msg_q(), domain_trn("pending"))))
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01302"
    assert response.json()[0]["id"] == "42"


def test_an_error_reply_without_a_result_is_a_500(http):
    response = answer(http, "get", "/messages", (False, "", "<epp/>"))
    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"
    assert response.json()["detail"] == "The reply of the EPP server cannot be read"


def test_ack_whose_reply_cannot_be_read_is_a_500(http):
    response = answer(http, "delete", "/messages/42", ok(1000, "not xml"))
    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"


ODD_SVTRIDS = [" sv-1", "sv-1 ", "  ", "日本", "a&#10;b", "a&#13;&#10;b", "a\u00e9b"]


def with_sv_trid(xml, value):
    return xml.replace("<svTRID>sv-1</svTRID>", f"<svTRID>{value}</svTRID>")


def assert_sane_headers(response):
    sv = response.headers["RPP-Svtrid"]
    assert sv and all(" " <= c <= "~" for c in sv)
    assert response.headers["RPP-Code"]
    assert response.headers["RPP-Cltrid"] == "msg-cl-1"


@pytest.mark.parametrize("value", ODD_SVTRIDS)
def test_an_odd_server_transaction_id_is_replaced_on_every_message_path(http, value):
    typed = ok(1301, with_sv_trid(reply(1301, msg_q(), domain_trn("pending")), value))
    raw = ok(1301, with_sv_trid(reply(1301, msg_q(), "<resData><foo/></resData>"), value))
    for reply_ in (typed, raw):
        response = answer(http, "get", "/messages", reply_)
        assert response.status_code == 200
        assert_sane_headers(response)
    ack = answer(http, "delete", "/messages/42", ok(1000, with_sv_trid(reply(1000, '<msgQ count="1" id="43"/>'), value)))
    assert ack.status_code == 200
    assert_sane_headers(ack)
    failed = answer(http, "delete", "/messages/42", (False, "2303", with_sv_trid(reply(2303), value)))
    assert failed.status_code == 404
    assert_sane_headers(failed)
    missing = answer(http, "get", "/messages/42", ok(1300, with_sv_trid(reply(1300), value)))
    assert missing.status_code == 404
    assert_sane_headers(missing)


def test_an_odd_server_transaction_id_is_logged_without_its_value(http):
    with capture_log() as captured:
        answer(http, "get", "/messages", ok(1301, with_sv_trid(reply(1301, msg_q()), "日本")))
    assert "transaction id" in captured.text
    assert "日本" not in captured.text


NO_DATE = '<msgQ count="1" id="9"><msg>Hi</msg></msgQ>'


@pytest.mark.parametrize("res_data,q", [
    (domain_trn("pending").replace("<domain:reDate>2026-11-05T16:49:34.0Z</domain:reDate>", ""), NO_DATE),
    (pan("domain", DOMAIN, "name", "1").replace("<domain:paDate>2026-11-06T10:00:00.0Z</domain:paDate>", ""), NO_DATE),
    (domain_trn("pending").replace("<domain:reDate>2026-11-05T16:49:34.0Z</domain:reDate>", ""),
     '<msgQ count="1" id="9"><qDate>garbage</qDate><msg>Hi</msg></msgQ>'),
])
def test_a_message_with_no_date_at_all_is_not_a_500(http, res_data, q):
    response = answer(http, "get", "/messages", ok(1301, reply(1301, q, res_data)))
    assert response.status_code == 200
    assert response.json()[0]["creationDate"]


def test_an_id_that_xml_allows_can_be_read_and_acked(http):
    zwj = "a%E2%80%8Db"
    assert answer(http, "delete", f"/messages/{zwj}", ok(1000, reply(1000, '<msgQ count="0"/>'))).status_code == 200
    xml = reply(1301, '<msgQ count="1" id="a&#8205;b"><qDate>2026-11-05T16:49:34.0Z</qDate><msg>Hi</msg></msgQ>')
    assert answer(http, "get", f"/messages/{zwj}", ok(1301, xml)).status_code == 200


def test_a_lone_surrogate_is_not_a_valid_id():
    with pytest.raises(ProblemException) as raised:
        _require_valid_id("a\ud800b")
    assert raised.value.status == 400


def test_problem_headers_replace_an_odd_server_transaction_id():
    assert problem_headers(ResultCode.OBJECT_DOES_NOT_EXIST, "日本")["RPP-Svtrid"] != "日本"
    assert problem_headers(ResultCode.OBJECT_DOES_NOT_EXIST, "ok-1")["RPP-Svtrid"] == "ok-1"


@pytest.mark.parametrize("id", ["%00", "%01", "%EF%BF%BE", "a%00b"])
@pytest.mark.parametrize("method", ["get", "delete"])
def test_an_id_with_control_characters_is_a_400_without_epp(http, id, method):
    response = answer(http, method, f"/messages/{id}")
    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02005"
    assert response.headers["RPP-Cltrid"] == "msg-cl-1"
    assert sent() == []


def test_epp_error_on_query(http):
    response = answer(http, "get", "/messages", (False, "2400", reply(2400)))
    assert response.status_code == 500
    assert response.headers["RPP-Code"] == "02400"


def test_read_of_the_head(http):
    response = answer(http, "get", "/messages/42", head())
    assert response.status_code == 200
    assert response.headers["RPP-Queue-Size"] == "3"
    assert response.headers["Content-Language"] == "en-US"
    assert response.json()["id"] == "42"
    assert 'op="req"' in sent()[-1]


def test_read_of_another_id_is_a_501(http):
    response = answer(http, "get", "/messages/43", head())
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == "02102"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Cltrid"] == "msg-cl-1"
    assert response.headers["RPP-Queue-Size"] == "3"
    assert len(sent()) == 1


def test_read_on_an_empty_queue_is_a_404(http):
    response = answer(http, "get", "/messages/42", ok(1300, reply(1300)))
    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"
    assert response.headers["RPP-Svtrid"] == "sv-1"
    assert response.headers["RPP-Queue-Size"] == "0"


def test_ack_sends_the_id_and_has_no_content(http):
    response = answer(http, "delete", "/messages/42", ok(1000, reply(1000, '<msgQ count="2" id="43"/>')))
    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.headers["RPP-Queue-Size"] == "2"
    assert response.headers["RPP-Cltrid"] == "msg-cl-1"
    assert response.content == b""
    assert "Content-Type" not in response.headers
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




def test_a_server_transaction_id_with_spaces_around_it_is_stripped(http):
    response = answer(http, "get", "/messages", ok(1301, with_sv_trid(reply(1301, msg_q()), " sv-7 ")))
    assert response.headers["RPP-Svtrid"] == "sv-7"
    failed = answer(http, "delete", "/messages/42", (False, "2303", with_sv_trid(reply(2303), " sv-8 ")))
    assert failed.headers["RPP-Svtrid"] == "sv-8"
