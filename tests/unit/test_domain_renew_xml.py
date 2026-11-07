import pytest
from lxml import etree

from epp_to_model_mapper import parse_domain_renew_response, renew_domain_xml
from models import DomainRenew, ResultCode

EPP = "urn:ietf:params:xml:ns:epp-1.0"
DOMAIN = "urn:ietf:params:xml:ns:domain-1.0"
NS = {"epp": EPP, "domain": DOMAIN}


def command(renew):
    return etree.fromstring(renew_domain_xml(renew, client_request_id="rn32-cl-1").encode())


def only(root, path):
    return root.xpath(path, namespaces=NS)


def test_renew_command():
    """RFC 5731 §3.2.3."""
    root = command(DomainRenew(name="foo.example", curExpDate="2005-04-03", duration="P5Y"))
    assert only(root, "//epp:renew/domain:renew/domain:name/text()") == ["foo.example"]
    assert only(root, "//domain:curExpDate/text()") == ["2005-04-03"]
    assert only(root, "//domain:period/text()") == ["5"]
    assert only(root, "//domain:period/@unit") == ["y"]
    assert only(root, "//epp:clTRID/text()") == ["rn32-cl-1"]


def test_without_a_period_none_is_sent():
    root = command(DomainRenew(name="foo.example", curExpDate="2005-04-03"))
    assert not only(root, "//domain:period")


def test_months():
    root = command(DomainRenew(name="foo.example", curExpDate="2005-04-03", duration="P6M"))
    assert only(root, "//domain:period/@unit") == ["m"]


def reply(code, res_data=""):
    return (
        f'<epp xmlns="{EPP}"><response><result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><clTRID>rn32-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


REN_DATA = (
    f'<resData><domain:renData xmlns:domain="{DOMAIN}"><domain:name>FOO.EXAMPLE</domain:name>'
    '<domain:exDate>2010-04-03T22:00:00.0Z</domain:exDate></domain:renData></resData>'
)


def test_ren_data_is_parsed():
    """RFC 5731 §3.2.3."""
    response = parse_domain_renew_response(reply(1000, REN_DATA), "rn32-cl-1")
    assert response.code == ResultCode.COMMAND_COMPLETED_SUCCESSFULLY
    assert response.renewal.name == "FOO.EXAMPLE"
    assert response.renewal.expiryDate == "2010-04-03T22:00:00.000000Z"
    assert response.server_transaction_id == "sv-1"


def test_reply_without_ren_data_has_no_expiry():
    response = parse_domain_renew_response(reply(1000), "rn32-cl-1")
    assert response.renewal.expiryDate is None
    assert response.renewal.name is None


def test_pending_reply():
    response = parse_domain_renew_response(reply(1001), "rn32-cl-1")
    assert response.code == ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    assert response.renewal.expiryDate is None


def test_pending_reply_with_ren_data_has_no_expiry():
    """The renewal has not completed (data-objects §10.3), so its new expiry is not reported."""
    response = parse_domain_renew_response(reply(1001, REN_DATA), "rn32-cl-1")
    assert response.code == ResultCode.COMMAND_COMPLETED_ACTION_PENDING
    assert response.renewal.expiryDate is None
