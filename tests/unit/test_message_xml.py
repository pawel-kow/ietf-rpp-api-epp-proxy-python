import pytest

from tests.helper.captured_log import capture_log
from lxml import etree

from epp_to_model_mapper.messages import parse_ack_response, parse_poll_response, poll_ack_xml, poll_request_xml
from models import ErrorResponse, PendingActionEvent, ResultCode, TransferEvent

EPP = "urn:ietf:params:xml:ns:epp-1.0"
NS = {"epp": EPP}
DOMAIN = "urn:ietf:params:xml:ns:domain-1.0"
CONTACT = "urn:ietf:params:xml:ns:contact-1.0"
HOST = "urn:ietf:params:xml:ns:host-1.0"


def command(xml):
    return etree.fromstring(xml.encode())


def test_poll_request_is_poll_req():
    root = command(poll_request_xml(client_request_id="msg-cl-1"))
    assert root.xpath("//epp:poll/@op", namespaces=NS) == ["req"]
    assert root.xpath("//epp:poll/@msgID", namespaces=NS) == []
    assert root.xpath("//epp:clTRID/text()", namespaces=NS) == ["msg-cl-1"]


def test_poll_ack_carries_the_message_id_escaped():
    root = command(poll_ack_xml('12"<&3', client_request_id="msg-cl-1"))
    assert root.xpath("//epp:poll/@op", namespaces=NS) == ["ack"]
    assert root.xpath("//epp:poll/@msgID", namespaces=NS) == ['12"<&3']


def reply(code, msg_q="", res_data="", extension="", msg="Message"):
    """RFC 5730 §2.9.2.3."""
    return (
        f'<epp xmlns="{EPP}"><response><result code="{code}"><msg>{msg}</msg></result>{msg_q}'
        f'{res_data}{extension}<trID><clTRID>msg-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def msg_q(text="Queue text.", count=3, id="42", extra=""):
    return (
        f'<msgQ count="{count}" id="{id}"><qDate>2026-11-05T16:49:34.0Z</qDate>'
        f'<msg lang="en-US">{text}</msg></msgQ>'
    )


def domain_trn(status, ex=""):
    return (
        f'<resData><domain:trnData xmlns:domain="{DOMAIN}"><domain:name>FOO.EXAMPLE</domain:name>'
        f'<domain:trStatus>{status}</domain:trStatus><domain:reID>baz</domain:reID>'
        '<domain:reDate>2026-11-05T16:49:34.0Z</domain:reDate><domain:acID>foo</domain:acID>'
        f'<domain:acDate>2026-11-05T16:54:34.0Z</domain:acDate>{ex}</domain:trnData></resData>'
    )


def contact_trn(status):
    return (
        f'<resData><contact:trnData xmlns:contact="{CONTACT}"><contact:id>FO-1</contact:id>'
        f'<contact:trStatus>{status}</contact:trStatus><contact:reID>baz</contact:reID>'
        '<contact:reDate>2026-11-05T16:49:34.0Z</contact:reDate><contact:acID>foo</contact:acID>'
        '<contact:acDate>2026-11-05T16:54:34.0Z</contact:acDate></contact:trnData></resData>'
    )


def pan(prefix, ns, id_element, result):
    return (
        f'<resData><{prefix}:panData xmlns:{prefix}="{ns}"><{prefix}:{id_element} paResult="{result}">X-1</{prefix}:{id_element}>'
        f'<{prefix}:paTRID><clTRID>cl-9</clTRID><svTRID>sv-9</svTRID></{prefix}:paTRID>'
        f'<{prefix}:paDate>2026-11-06T10:00:00.0Z</{prefix}:paDate></{prefix}:panData></resData>'
    )


def parse(xml):
    return parse_poll_response(xml, "msg-cl-1")


def test_empty_queue_has_no_message():
    resp = parse(reply(1300))
    assert resp.code == ResultCode.COMMAND_COMPLETED_NO_MESSAGES
    assert resp.message is None
    assert resp.queue_size == 0


def test_message_header_fields():
    resp = parse(reply(1301, msg_q(), domain_trn("pending")))
    assert resp.code == ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE
    assert resp.queue_size == 3
    assert resp.message.id == "42"
    assert resp.message.creationDate == "2026-11-05T16:49:34.000000Z"
    assert resp.message.lang == "en-US"
    assert resp.message.text == "Queue text."
    assert resp.server_transaction_id == "sv-1"


def test_domain_transfer_pending():
    event = parse(reply(1301, msg_q(), domain_trn("pending", "<domain:exDate>2028-11-05T16:49:18.0Z</domain:exDate>"))).message.event
    assert isinstance(event, TransferEvent)
    assert (event.objectType, event.objectId, event.trStatus) == ("domainName", "FOO.EXAMPLE", "pending")
    assert event.requestDate == "2026-11-05T16:49:34.000000Z"
    assert event.actionDate == "2026-11-05T16:54:34.000000Z"
    assert event.expiryDate == "2028-11-05T16:49:18.000000Z"
    assert event.process.name == "FOO.EXAMPLE"
    assert event.process.reqClientId == "baz"


@pytest.mark.parametrize("status", ["clientApproved", "clientCancelled", "clientRejected", "serverApproved", "serverCancelled"])
def test_domain_transfer_outcome_status(status):
    event = parse(reply(1301, msg_q(), domain_trn(status))).message.event
    assert event.trStatus == status


def test_contact_transfer():
    event = parse(reply(1301, msg_q(), contact_trn("serverApproved"))).message.event
    assert (event.objectType, event.objectId, event.trStatus) == ("contact", "FO-1", "serverApproved")
    assert event.process.id == "FO-1"


@pytest.mark.parametrize("prefix,ns,element,object_type", [
    ("domain", DOMAIN, "name", "domainName"),
    ("contact", CONTACT, "id", "contact"),
    ("host", HOST, "name", "host"),
])
@pytest.mark.parametrize("result,approved", [("1", True), ("0", False), ("true", True), ("false", False)])
def test_pending_action_reply(prefix, ns, element, object_type, result, approved):
    event = parse(reply(1301, msg_q(), pan(prefix, ns, element, result))).message.event
    assert isinstance(event, PendingActionEvent)
    assert (event.objectType, event.objectId, event.approved) == (object_type, "X-1", approved)
    assert event.clientTransactionId == "cl-9"
    assert event.serverTransactionId == "sv-9"
    assert event.completionDate == "2026-11-06T10:00:00.000000Z"


def test_message_without_res_data_has_no_event_and_nothing_unmapped():
    message = parse(reply(1301, msg_q("Hello."))).message
    assert message.event is None
    assert message.unmapped is None
    assert message.text == "Hello."


def test_unknown_res_data_is_named():
    res = '<resData><x:other xmlns:x="urn:example:x"><x:a>1</x:a></x:other></resData>'
    message = parse(reply(1301, msg_q(), res)).message
    assert message.event is None
    assert "urn:example:x" in message.unmapped
    assert "other" in message.unmapped


def test_response_extension_makes_the_message_unmapped():
    ext = '<extension><x:ext xmlns:x="urn:example:x"/></extension>'
    message = parse(reply(1301, msg_q(), domain_trn("pending"), ext)).message
    assert message.event is None
    assert "urn:example:x" in message.unmapped


def test_two_res_data_elements_make_the_message_unmapped():
    res = domain_trn("pending").replace("</resData>", f'<x:other xmlns:x="urn:example:x"/></resData>')
    message = parse(reply(1301, msg_q(), res)).message
    assert message.event is None
    assert "urn:example:x" in message.unmapped


def test_transfer_with_unknown_status_is_unmapped_not_an_error():
    message = parse(reply(1301, msg_q(), domain_trn("pending").replace(">pending<", ">weird<"))).message
    assert message.event is None
    assert message.unmapped


def test_message_text_with_mixed_content():
    q = '<msgQ count="1" id="7"><qDate>2026-11-05T16:49:34.0Z</qDate><msg>Hello <b>big</b> world</msg></msgQ>'
    message = parse(reply(1301, q)).message
    assert message.text == "Hello big world"
    assert message.lang == "en"


def test_ack_reply_with_queue_size():
    resp = parse_ack_response(reply(1000, '<msgQ count="4" id="43"/>'), "msg-cl-1")
    assert resp.code == ResultCode.COMMAND_COMPLETED_SUCCESSFULLY
    assert resp.queue_size == 4


def test_ack_reply_without_msg_q_has_no_queue_size():
    assert parse_ack_response(reply(1000), "msg-cl-1").queue_size is None


def test_text_is_joined_and_then_trimmed():
    assert parse(reply(1301, msg_q("  Pay<b>load</b>.  "))).message.text == "Payload."


def test_markup_with_attributes_is_named_as_unmapped():
    q = '<msgQ count="1" id="7"><qDate>2026-11-05T16:49:34.0Z</qDate><msg><field name="x" value="y"/></msg></msgQ>'
    message = parse(reply(1301, q)).message
    assert message.text == ""
    assert "field" in message.unmapped


@pytest.mark.parametrize("bad", ["garbage", "2026-13-45T00:00:00Z", "2026-01-01T23:59:60Z", "", "2026-01-01T24:00:00Z", "2026-01-01T00:00:00+99:00"])
def test_a_bad_q_date_is_missing_and_the_message_is_still_mapped(bad):
    q = f'<msgQ count="1" id="7"><qDate>{bad}</qDate><msg>Hi</msg></msgQ>'
    with capture_log() as caplog:
        message = parse(reply(1301, q, domain_trn("pending"))).message
    assert message.creationDate is None
    assert isinstance(message.event, TransferEvent)
    assert "date" in caplog.text


def test_message_without_q_date():
    q = '<msgQ count="1" id="7"><msg>Hi</msg></msgQ>'
    assert parse(reply(1301, q)).message.creationDate is None


@pytest.mark.parametrize("res_data", [
    domain_trn("pending").replace("</domain:trnData>", "<domain:extra>SECRET</domain:extra></domain:trnData>"),
    domain_trn("pending").replace("<domain:trStatus>pending</domain:trStatus>", "<domain:trStatus>pending</domain:trStatus>" * 2),
    '<resData><other xmlns="">SECRET</other></resData>',
    '<resData><foo>SECRET</foo></resData>',
])
def test_a_reply_that_does_not_follow_the_schema_is_still_a_message(res_data):
    with capture_log() as caplog:
        resp = parse(reply(1301, msg_q("Odd."), res_data))
    assert resp.message.id == "42"
    assert resp.message.text == "Odd."
    assert resp.message.event is None
    assert resp.message.unmapped
    assert resp.queue_size == 3
    assert resp.server_transaction_id == "sv-1"
    assert "SECRET" not in caplog.text and "SECRET" not in resp.message.unmapped


@pytest.mark.parametrize("q", [
    '<msgQ count="3" id="42"><qDate>2026-11-05T16:49:34.0Z</qDate><msg>One</msg><msg>Two</msg></msgQ>',
    '<msgQ count="3" id="42"><qDate>2026-11-05T16:49:34.0Z</qDate><qDate>2026-11-05T16:49:34.0Z</qDate><msg>One</msg></msgQ>',
    '<msgQ count="3" id="42"><qDate>2026-11-05T16:49:34.0Z</qDate><unknown/><msg>One</msg></msgQ>',
])
def test_a_msg_q_that_does_not_follow_the_schema_keeps_id_and_count(q):
    message = parse(reply(1301, q)).message
    assert message.id == "42"
    assert message.creationDate


def test_unknown_child_in_a_known_extension_is_still_a_message():
    ext = '<extension><rgp:infData xmlns:rgp="urn:ietf:params:xml:ns:rgp-1.0"><rgp:bogus>SECRET</rgp:bogus></rgp:infData></extension>'
    with capture_log() as caplog:
        message = parse(reply(1301, msg_q(), "", ext)).message
    assert message.id == "42"
    assert "rgp-1.0" in message.unmapped
    assert "SECRET" not in caplog.text


@pytest.mark.parametrize("res_data,names", [
    ('<resData><x:other xmlns:x="urn:example:x">SECRET</x:other></resData>', ["urn:example:x", "other"]),
    (domain_trn("pending").replace("</resData>", '<x:other xmlns:x="urn:example:x">SECRET</x:other></resData>'), ["urn:example:x"]),
])
def test_untranslated_data_is_logged_by_name_and_never_by_content(res_data, names):
    with capture_log() as caplog:
        parse(reply(1301, msg_q(), res_data))
    for name in names:
        assert name in caplog.text
    assert "SECRET" not in caplog.text


def test_extension_is_logged_by_name():
    with capture_log() as caplog:
        parse(reply(1301, msg_q(), "", '<extension><x:ext xmlns:x="urn:example:ext">SECRET</x:ext></extension>'))
    assert "urn:example:ext" in caplog.text and "SECRET" not in caplog.text


def test_pa_result_that_is_no_boolean_is_not_an_approval():
    message = parse(reply(1301, msg_q(), pan("domain", DOMAIN, "name", "maybe"))).message
    assert message.event is None
    assert message.unmapped


def test_pa_result_is_read_as_a_boolean_without_a_server_transaction_id_too():
    res = pan("domain", DOMAIN, "name", "1").replace("<svTRID>sv-9</svTRID>", "")
    assert parse(reply(1301, msg_q(), res)).message.event.serverTransactionId is None


@pytest.mark.parametrize("res_data", [
    domain_trn("pending").replace("<domain:name>FOO.EXAMPLE</domain:name>", ""),
    contact_trn("pending").replace("<contact:id>FO-1</contact:id>", ""),
    pan("domain", DOMAIN, "name", "1").replace(">X-1<", "><"),
])
def test_object_without_an_id_is_unmapped(res_data):
    message = parse(reply(1301, msg_q(), res_data)).message
    assert message.event is None
    assert message.unmapped


def test_data_name_is_carried_for_a_mapped_event():
    assert "trnData" in parse(reply(1301, msg_q(), domain_trn("pending"))).message.data_name


@pytest.mark.parametrize("q", ["", '<msgQ count="3"/>', '<msgQ count="3" id=""/>'])
def test_1301_without_a_message_id_is_not_an_empty_queue(q):
    with capture_log() as caplog:
        resp = parse(reply(1301, q))
    assert isinstance(resp, ErrorResponse)
    assert resp.code == ResultCode.COMMAND_FAILED
    assert resp.server_transaction_id == "sv-1"
    assert "without a message id" in caplog.text


def test_reply_without_tr_id_is_still_read():
    xml = reply(1301, msg_q()).replace('<trID><clTRID>msg-cl-1</clTRID><svTRID>sv-1</svTRID></trID>', "")
    resp = parse(xml)
    assert resp.message.id == "42"
    assert resp.server_transaction_id is None


def test_unknown_success_code_is_carried_as_it_is():
    """Core §18.1: a code not in Table 9 is mapped by Table 10, and RPP-Code stays the EPP code with a leading 0."""
    resp = parse(reply(1302, msg_q(), domain_trn("pending")))
    assert resp.code.value[0] == "1302"
    assert resp.message.id == "42"


def test_unknown_code_is_logged_by_number(log):
    with log() as captured:
        parse(reply(1302, msg_q()))
    assert "1302" in captured.text


def test_ack_without_tr_id_and_with_unknown_code_is_not_an_error():
    xml = reply(1302, '<msgQ count="4" id="43"/>').replace('<trID><clTRID>msg-cl-1</clTRID><svTRID>sv-1</svTRID></trID>', "")
    resp = parse_ack_response(xml, "msg-cl-1")
    assert resp.queue_size == 4
    assert resp.code.value[0] == "1302"


@pytest.mark.parametrize("xml", ["not xml at all", "", "<epp/>"])
def test_ack_reply_without_a_readable_result_is_an_error(xml):
    resp = parse_ack_response(xml, "msg-cl-1")
    assert isinstance(resp, ErrorResponse)
    assert resp.code == ResultCode.COMMAND_FAILED


def test_ack_with_a_msg_q_that_does_not_follow_the_schema():
    resp = parse_ack_response(reply(1000, '<msgQ count="2" id="43"><unknown/></msgQ>'), "msg-cl-1")
    assert resp.queue_size == 2


@pytest.mark.parametrize("xml", ["not xml at all", "<epp/>"])
def test_unreadable_poll_reply_is_an_error(xml):
    assert isinstance(parse(xml), ErrorResponse)


@pytest.fixture
def log():
    return capture_log


def test_the_server_transaction_id_is_the_one_of_the_reply_and_not_of_a_pending_action():
    res = pan("domain", DOMAIN, "name", "1") + '<unknown/>'  # makes the typed parser fail
    resp = parse(reply(1301, msg_q(), res))
    assert resp.server_transaction_id == "sv-1"


def test_markup_with_attributes_in_msg_is_named_on_the_raw_path_too():
    q = '<msgQ count="1" id="7"><msg><field name="x" value="y"/></msg><unknown/></msgQ>'
    message = parse(reply(1301, q)).message
    assert "field" in message.unmapped


def test_data_that_does_not_map_is_logged_by_name_and_not_by_content(log):
    res = pan("domain", DOMAIN, "name", "maybe").replace(">X-1<", ">SECRET<")
    with log() as captured:
        parse(reply(1301, msg_q(), res))
    assert "panData" in captured.text
    assert "SECRET" not in captured.text


def test_markup_in_the_text_is_logged_by_name_and_not_by_content(log):
    q = '<msgQ count="1" id="7"><msg><field name="SECRET" value="SECRET"/></msg></msgQ>'
    with log() as captured:
        parse(reply(1301, q))
    assert "field" in captured.text
    assert "SECRET" not in captured.text


def test_reply_that_does_not_follow_the_schema_is_logged_by_name_and_not_by_content(log):
    res = '<resData><foo>SECRET</foo></resData>'
    with log() as captured:
        parse(reply(1301, msg_q("SECRET text"), res))
    assert "does not follow" in captured.text
    assert "foo" in captured.text
    assert "SECRET" not in captured.text


def test_ack_reply_that_does_not_follow_the_schema_is_logged(log):
    with log() as captured:
        parse_ack_response(reply(1000, '<msgQ count="2" id="43"><unknown/></msgQ>'), "msg-cl-1")
    assert "does not follow" in captured.text


def test_a_message_without_an_id_is_logged_on_the_raw_path_too(log):
    with log() as captured:
        parse(reply(1301, '<msgQ count="3"/>' + '<unknown/>'))
    assert "without a message id" in captured.text


def test_text_after_a_comment_is_kept():
    assert parse(reply(1301, msg_q("Queue<!-- c --> text."))).message.text == "Queue text."


def test_text_after_a_comment_is_kept_on_every_operation():
    from epp_to_model_mapper import parse_domain_check_response_single
    xml = reply(1000, (
        f'<resData><domain:chkData xmlns:domain="{DOMAIN}"><domain:cd><domain:name avail="1">exa<!-- c -->mple.test'
        '</domain:name></domain:cd></domain:chkData></resData>'
    ))
    assert parse_domain_check_response_single(xml, "example.test", "msg-cl-1").available is True


def test_a_bare_doctype_is_refused_on_the_typed_path():
    from epp_to_model_mapper.commands.helper import str_to_epp
    with pytest.raises(ValueError):
        str_to_epp('<!DOCTYPE epp>' + reply(1300))


def test_a_message_id_cannot_inject_a_log_line(log):
    evil = "4&#10;FAKE LOG LINE"
    q = f'<msgQ count="1" id="{evil}"><qDate>2026-11-05T16:49:34.0Z</qDate><msg><field a="b"/></msg></msgQ>'
    xmls = [
        reply(1301, q, '<resData><x:other xmlns:x="urn:example:x"/></resData>'),
        reply(1301, q, domain_trn("pending").replace("</resData>", '<x:other xmlns:x="urn:example:x"/></resData>')),
        reply(1301, q, domain_trn("pending"), '<extension><x:e xmlns:x="urn:example:x"/></extension>'),
        reply(1301, q, pan("domain", DOMAIN, "name", "maybe")),
        reply(1301, q),
        reply(1301, q, "<resData><foo/></resData>"),
    ]
    with log() as captured:
        for xml in xmls:
            parse(xml)
    assert len(captured.lines) >= 6
    assert all("\n" not in line for line in captured.lines)
