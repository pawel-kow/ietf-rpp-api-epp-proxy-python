import pytest
from lxml import etree

from epp_to_model_mapper.messages import parse_ack_response, parse_poll_response, poll_ack_xml, poll_request_xml
from models import PendingActionEvent, ResultCode, TransferEvent

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
    assert "Hello" in message.text and "world" in message.text
    assert message.lang == "en"


def test_ack_reply_with_queue_size():
    resp = parse_ack_response(reply(1000, '<msgQ count="4" id="43"/>'), "msg-cl-1")
    assert resp.code == ResultCode.COMMAND_COMPLETED_SUCCESSFULLY
    assert resp.queue_size == 4


def test_ack_reply_without_msg_q_has_no_queue_size():
    assert parse_ack_response(reply(1000), "msg-cl-1").queue_size is None
