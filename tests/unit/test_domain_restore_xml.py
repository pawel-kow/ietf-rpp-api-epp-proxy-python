from lxml import etree

from registry_adapter.epp.commands.domain.domain_xml import (
    parse_domain_response, parse_domain_restore_response, restore_domain_xml,
)
from core.model.domain.domain_restore import DomainRestore
from core.model.domain.restore_report import RestoreReport
from core.result.result_code import ResultCode
from tests.helper.epp_ns_map import EPP_NS_MAP

EPP = "urn:ietf:params:xml:ns:epp-1.0"
DOMAIN = "urn:ietf:params:xml:ns:domain-1.0"
RGP = "urn:ietf:params:xml:ns:rgp-1.0"
NS = {"epp": EPP, "domain": DOMAIN, "rgp": RGP}
REPORT = RestoreReport(
    preData="Pre-delete registration data.",
    postData="Post-restore registration data.",
    deleteTime="2003-07-10T22:00:00.0Z",
    restoreTime="2003-07-20T22:00:00.0Z",
    restoreReason="Registrant error.",
    statements=["First statement.", "Second statement."],
)


def command(restore):
    return etree.fromstring(restore_domain_xml(restore, client_request_id="rs35-cl-1", ns_map=EPP_NS_MAP).encode())


def only(root, path):
    return root.xpath(path, namespaces=NS)


def test_request_command():
    """RFC 3915 §4.2.5: a domain update with an empty chg and the restore request."""
    root = command(DomainRestore(name="foo.example"))
    assert only(root, "//epp:update/domain:update/domain:name/text()") == ["FOO.EXAMPLE"]
    chg = only(root, "//domain:update/domain:chg")
    assert len(chg) == 1 and len(chg[0]) == 0
    assert not only(root, "//domain:add") and not only(root, "//domain:rem")
    assert only(root, "//epp:extension/rgp:update/rgp:restore/@op") == ["request"]
    assert not only(root, "//rgp:report")
    assert only(root, "//epp:clTRID/text()") == ["rs35-cl-1"]


def test_report_command():
    """RFC 3915 §4.2.5: the report, in the order of the schema."""
    root = command(DomainRestore(name="foo.example", report=REPORT))
    assert only(root, "//rgp:restore/@op") == ["report"]
    report = only(root, "//rgp:restore/rgp:report")[0]
    assert [etree.QName(child).localname for child in report] == [
        "preData", "postData", "delTime", "resTime", "resReason", "statement", "statement",
    ]
    assert only(report, "rgp:preData/text()") == ["Pre-delete registration data."]
    assert only(report, "rgp:postData/text()") == ["Post-restore registration data."]
    assert only(report, "rgp:delTime/text()") == ["2003-07-10T22:00:00Z"]  # the same instant
    assert only(report, "rgp:resTime/text()") == ["2003-07-20T22:00:00Z"]
    assert only(report, "rgp:resReason/text()") == ["Registrant error."]
    assert only(report, "rgp:statement/text()") == ["First statement.", "Second statement."]
    assert not only(report, "rgp:other")


def test_report_with_other():
    root = command(DomainRestore(name="foo.example", report=RestoreReport(**{**REPORT.__dict__, "other": "More."})))
    assert only(root, "//rgp:report/rgp:other/text()") == ["More."]


def test_report_text_is_escaped():
    report = RestoreReport(**{**REPORT.__dict__, "preData": "<domain:name>a & b</domain:name>"})
    root = command(DomainRestore(name="foo.example", report=report))
    assert only(root, "//rgp:preData/text()") == ["<domain:name>a & b</domain:name>"]


def reply(code, extension=""):
    return (
        f'<epp xmlns="{EPP}"><response><result code="{code}"><msg>Message</msg></result>{extension}'
        '<trID><clTRID>rs35-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def up_data(*statuses):
    inner = "".join(f'<rgp:rgpStatus s="{s}"/>' for s in statuses)
    return f'<extension><rgp:upData xmlns:rgp="{RGP}">{inner}</rgp:upData></extension>'


def test_request_reply_with_up_data():
    resp = parse_domain_restore_response(reply(1000, up_data("pendingRestore")), DomainRestore(name="foo.example"), "rs35-cl-1")
    assert resp.code == ResultCode.COMMAND_COMPLETED_SUCCESSFULLY
    assert resp.server_transaction_id == "sv-1"
    assert resp.restore.rgpStatus == ["pendingRestore"]


def test_request_reply_without_up_data_is_pending_restore():
    """RFC 3915 §3.2: an accepted request puts the domain in pendingRestore."""
    resp = parse_domain_restore_response(reply(1000), DomainRestore(name="foo.example"), "rs35-cl-1")
    assert resp.restore.rgpStatus == ["pendingRestore"]


def test_report_reply_without_up_data_is_restored():
    resp = parse_domain_restore_response(reply(1000), DomainRestore(name="foo.example", report=REPORT), "rs35-cl-1")
    assert resp.restore.rgpStatus == []


def test_pending_report_reply_is_pending_restore():
    resp = parse_domain_restore_response(reply(1001), DomainRestore(name="foo.example", report=REPORT), "rs35-cl-1")
    assert resp.restore.rgpStatus == ["pendingRestore"]


def test_report_reply_with_up_data_follows_it():
    restore = DomainRestore(name="foo.example", report=REPORT)
    resp = parse_domain_restore_response(reply(1000, up_data("pendingRestore")), restore, "rs35-cl-1")
    assert resp.restore.rgpStatus == ["pendingRestore"]


def info_reply(extension=""):
    return (
        f'<epp xmlns="{EPP}"><response><result code="1000"><msg>Message</msg></result>'
        f'<resData><domain:infData xmlns:domain="{DOMAIN}"><domain:name>FOO.EXAMPLE</domain:name>'
        '<domain:roid>D1-EX</domain:roid><domain:status s="pendingDelete"/><domain:clID>user</domain:clID>'
        f'</domain:infData></resData>{extension}'
        '<trID><clTRID>rs35-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def test_info_reads_the_rgp_status():
    """RFC 3915 §4.1.2."""
    extension = f'<extension><rgp:infData xmlns:rgp="{RGP}"><rgp:rgpStatus s="redemptionPeriod"/></rgp:infData></extension>'
    assert parse_domain_response(info_reply(extension), "rs35-cl-1").domain.rgpStatus == ["redemptionPeriod"]


def test_info_without_rgp_data_has_no_rgp_status():
    assert parse_domain_response(info_reply(), "rs35-cl-1").domain.rgpStatus == []
