import pytest

from flows import patch_domain
from models import Domain, DomainUpdate, DomainUpdateRemove, ErrorResponse, HostObj, NS
from tests.helper.fake_epp_client import FakeEppClient

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'
NAME = "foo.example"


def epp_reply(code, res_data=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def info(*hosts):
    ns = "".join(f"<domain:hostObj>{host}</domain:hostObj>" for host in hosts)
    return (True, "1000", epp_reply(1000, (
        f'<resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name><domain:roid>D1</domain:roid>'
        f'<domain:status s="ok"/><domain:ns>{ns}</domain:ns><domain:clID>foo</domain:clID><domain:crID>foo</domain:crID>'
        '<domain:crDate>2026-11-04T10:00:00.0Z</domain:crDate></domain:infData></resData>'
    )))


DONE = (True, "1000", epp_reply(1000))
MISSING = (False, "2303", epp_reply(2303))
REMOVE_NS1 = DomainUpdate(name=NAME, remove=DomainUpdateRemove(ns=NS(host_objs=[HostObj(id="ns1.foo.example")], host_attrs=None)))


def client(*replies):
    return FakeEppClient("u", "p", replies=replies)


def never_called(domain: Domain):
    raise AssertionError("the patch needs no current domain")


def test_a_direct_update_is_not_preceded_by_a_read():
    epp = client(DONE, info("ns2.foo.example"))

    result = patch_domain(epp, NAME, REMOVE_NS1, never_called, "cl-1")

    assert len(epp.sent) == 2
    assert "domain:update" in epp.sent[0] and "domain:info" in epp.sent[1]
    assert result.domain.ns.host_objs == [HostObj(id="ns2.foo.example")]


def test_a_patch_needing_the_domain_reads_it_first():
    epp = client(info("ns1.foo.example"), DONE, info())
    seen = []

    def from_current(domain):
        seen.append(domain)
        return REMOVE_NS1

    result = patch_domain(epp, NAME, None, from_current, "cl-1")

    assert seen[0].ns.host_objs == [HostObj(id="ns1.foo.example")]
    assert [("domain:info" in m, "domain:update" in m) for m in epp.sent] == [(True, False), (False, True), (True, False)]
    assert result.mutation.server_transaction_id == "sv-1"


def test_a_failed_read_is_returned():
    result = patch_domain(client(MISSING), NAME, None, never_called, "cl-1")

    assert isinstance(result, ErrorResponse)


def test_a_patch_that_changes_nothing_sends_no_update():
    epp = client(info("ns1.foo.example"))

    result = patch_domain(epp, NAME, None, lambda domain: DomainUpdate(name=NAME), "cl-1")

    assert len(epp.sent) == 1
    assert result.domain.name.lower() == NAME


def test_a_rejected_update_is_returned():
    assert isinstance(patch_domain(client(MISSING), NAME, REMOVE_NS1, never_called, "cl-1"), ErrorResponse)


def test_failed_readback_has_no_domain():
    result = patch_domain(client(DONE, MISSING), NAME, REMOVE_NS1, never_called, "cl-1")

    assert result.domain is None
    assert result.mutation.server_transaction_id == "sv-1"


def test_exception_during_readback_has_no_domain():
    assert patch_domain(client(DONE, ConnectionError("gone")), NAME, REMOVE_NS1, never_called, "cl-1").domain is None


def test_error_of_the_patch_propagates():
    def conflict(domain):
        raise ValueError("no")

    with pytest.raises(ValueError):
        patch_domain(client(info()), NAME, None, conflict, "cl-1")
