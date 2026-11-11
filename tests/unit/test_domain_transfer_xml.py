import pytest
from lxml import etree

from registry_adapter.epp.commands.domain.domain_xml import parse_domain_transfer_response, transfer_domain_xml
from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.common import AuthInfo
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.model.shared.transfer_operation import TransferOperation
from core.result.result_code import ResultCode
from tests.helper.epp_ns_map import EPP_NS_MAP

EPP = "urn:ietf:params:xml:ns:epp-1.0"
DOMAIN = "urn:ietf:params:xml:ns:domain-1.0"
NS = {"epp": EPP, "domain": DOMAIN}


def command(transfer):
    return etree.fromstring(transfer_domain_xml(transfer, client_request_id="cl-1", ns_map=EPP_NS_MAP).encode())


def only(root, path):
    return root.xpath(path, namespaces=NS)


@pytest.mark.parametrize("operation", list(TransferOperation))
def test_operation_is_the_op_attribute(operation):
    root = command(DomainTransfer(name="foo.example", operation=operation))
    assert only(root, "//epp:transfer/@op") == [operation.value]
    assert only(root, "//epp:transfer/domain:transfer/domain:name/text()") == ["foo.example"]
    assert only(root, "//epp:clTRID/text()") == ["cl-1"]


def test_without_period_and_auth_info_neither_is_sent():
    root = command(DomainTransfer(name="foo.example", operation=TransferOperation.QUERY))
    assert not only(root, "//domain:period")
    assert not only(root, "//domain:authInfo")


@pytest.mark.parametrize("duration,value,unit", [("P1Y", "1", "y"), ("P6M", "6", "m")])
def test_period(duration, value, unit):
    root = command(DomainTransfer(name="foo.example", operation=TransferOperation.REQUEST, duration=duration))
    assert only(root, "//domain:period/text()") == [value]
    assert only(root, "//domain:period/@unit") == [unit]


def test_auth_info_is_escaped_and_carries_the_roid():
    auth_info = AuthInfo(pw="a<b&c", roid="REG-123")
    root = command(DomainTransfer(name="foo.example", operation=TransferOperation.REQUEST, authInfo=auth_info))
    assert only(root, "//domain:authInfo/domain:pw/text()") == ["a<b&c"]
    assert only(root, "//domain:authInfo/domain:pw/@roid") == ["REG-123"]


def reply(code, ex_date=""):
    """RFC 5731 §3.2.4."""
    return (
        f'<epp xmlns="{EPP}"><response><result code="{code}"><msg>Message</msg></result>'
        f'<resData><domain:trnData xmlns:domain="{DOMAIN}"><domain:name>FOO.EXAMPLE</domain:name>'
        '<domain:trStatus>pending</domain:trStatus><domain:reID>ClientX</domain:reID>'
        '<domain:reDate>2000-06-08T22:00:00.0Z</domain:reDate><domain:acID>ClientY</domain:acID>'
        f'<domain:acDate>2000-06-13T22:00:00.0Z</domain:acDate>{ex_date}</domain:trnData></resData>'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def test_trn_data_is_parsed():
    response = parse_domain_transfer_response(
        reply(1001, "<domain:exDate>2002-09-08T22:00:00.0Z</domain:exDate>"), "cl-1",
    )
    assert response.code == ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    assert response.server_transaction_id == "sv-1"
    assert response.transfer == DomainTransferProcess(
        name="FOO.EXAMPLE",
        trStatus="pending",
        reqClientId="ClientX",
        requestDate="2000-06-08T22:00:00.000000Z",
        actClientId="ClientY",
        actionDate="2000-06-13T22:00:00.000000Z",
        expiryDate="2002-09-08T22:00:00.000000Z",
    )


def test_expiry_date_is_optional():
    assert parse_domain_transfer_response(reply(1000), "cl-1").transfer.expiryDate is None
