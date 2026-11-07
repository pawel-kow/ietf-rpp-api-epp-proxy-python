import pytest
from lxml import etree

from epp_to_model_mapper import parse_contact_transfer_response, transfer_contact_xml
from models import AuthInfo, ContactTransfer, ContactTransferProcess, ResultCode, TransferOperation

EPP = "urn:ietf:params:xml:ns:epp-1.0"
CONTACT = "urn:ietf:params:xml:ns:contact-1.0"
NS = {"epp": EPP, "contact": CONTACT}


def command(transfer):
    return etree.fromstring(transfer_contact_xml(transfer, client_request_id="cl-1").encode())


def only(root, path):
    return root.xpath(path, namespaces=NS)


@pytest.mark.parametrize("operation", list(TransferOperation))
def test_operation_is_the_op_attribute(operation):
    root = command(ContactTransfer(id="FO-1", operation=operation))
    assert only(root, "//epp:transfer/@op") == [operation.value]
    assert only(root, "//epp:transfer/contact:transfer/contact:id/text()") == ["FO-1"]
    assert only(root, "//epp:clTRID/text()") == ["cl-1"]


def test_without_auth_info_none_is_sent():
    root = command(ContactTransfer(id="FO-1", operation=TransferOperation.QUERY))
    assert not only(root, "//contact:authInfo")


def test_auth_info_is_escaped_and_carries_the_roid():
    auth_info = AuthInfo(pw="a<b&c", roid="REG-123")
    root = command(ContactTransfer(id="FO-1", operation=TransferOperation.REQUEST, authInfo=auth_info))
    assert only(root, "//contact:authInfo/contact:pw/text()") == ["a<b&c"]
    assert only(root, "//contact:authInfo/contact:pw/@roid") == ["REG-123"]


def reply(code):
    """RFC 5733 §3.2.4."""
    return (
        f'<epp xmlns="{EPP}"><response><result code="{code}"><msg>Message</msg></result>'
        f'<resData><contact:trnData xmlns:contact="{CONTACT}"><contact:id>FO-1</contact:id>'
        '<contact:trStatus>pending</contact:trStatus><contact:reID>ClientX</contact:reID>'
        '<contact:reDate>2000-06-08T22:00:00.0Z</contact:reDate><contact:acID>ClientY</contact:acID>'
        '<contact:acDate>2000-06-13T22:00:00.0Z</contact:acDate></contact:trnData></resData>'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def test_trn_data_is_parsed():
    response = parse_contact_transfer_response(reply(1001), "cl-1")
    assert response.code == ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    assert response.server_transaction_id == "sv-1"
    assert response.transfer == ContactTransferProcess(
        id="FO-1",
        trStatus="pending",
        reqClientId="ClientX",
        requestDate="2000-06-08T22:00:00.000000Z",
        actClientId="ClientY",
        actionDate="2000-06-13T22:00:00.000000Z",
    )
