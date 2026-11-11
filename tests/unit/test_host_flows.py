import pytest

from registry_adapter.epp.gateways.epp_backend import EppBackend
from flows import create_host, patch_host, replace_host, update_host
from models import ErrorResponse, Host, HostReplacement, HostUpdate, HostUpdateChanges, ResultCode
from tests.helper.fake_epp_client import FakeEppClient
from tests.helper.epp_ns_map import EPP_NS_MAP

HOST_NS = 'xmlns:host="urn:ietf:params:xml:ns:host-1.0"'
NAME = "ns1.example.example"


def epp_reply(code, res_data=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def info(statuses=("ok",), addresses=(), reasons=None):
    reasons = reasons or {}
    status = "".join(f'<host:status s="{s}">{reasons.get(s, "")}</host:status>' for s in statuses)
    addr = "".join(f'''<host:addr ip="{"v6" if ":" in a else "v4"}">{a}</host:addr>''' for a in addresses)
    return (True, "1000", epp_reply(1000, (
        f'<resData><host:infData {HOST_NS}><host:name>NS1.EXAMPLE.EXAMPLE</host:name><host:roid>H1</host:roid>'
        f'{status}{addr}<host:clID>foo</host:clID><host:crID>foo</host:crID>'
        '<host:crDate>2026-11-04T10:00:00.0Z</host:crDate></host:infData></resData>'
    )))


DONE = (True, "1000", epp_reply(1000))
CREATED = (True, "1000", epp_reply(1000, (
    f'<resData><host:creData {HOST_NS}><host:name>NS1.EXAMPLE.EXAMPLE</host:name>'
    '<host:crDate>2026-11-04T10:00:00.0Z</host:crDate></host:creData></resData>'
)))
MISSING = (False, "2303", epp_reply(2303))
EXISTS = (False, "2302", epp_reply(2302))


def client(*replies, username="foo"):
    return FakeEppClient(username, "p", replies=replies)


def replacement(new_name, **members):
    """The host `NAME` as a full update asks for it."""
    return HostReplacement(name=NAME, new_name=new_name, **members)


def test_create_reads_the_host_back():
    result = create_host(EppBackend(client(CREATED, info()), EPP_NS_MAP), Host(name=NAME), "cl-1")

    assert result.host.status == ["ok"]
    assert result.mutation.server_transaction_id == "sv-1"


def test_create_error_is_returned():
    assert isinstance(create_host(EppBackend(client(EXISTS), EPP_NS_MAP), Host(name=NAME), "cl-1"), ErrorResponse)


def test_failed_readback_has_no_host():
    result = create_host(EppBackend(client(CREATED, MISSING), EPP_NS_MAP), Host(name=NAME), "cl-1")

    assert result.host is None
    assert result.mutation.server_transaction_id == "sv-1"


def test_exception_during_readback_has_no_host():
    result = update_host(EppBackend(client(DONE, ConnectionError("gone")), EPP_NS_MAP), HostUpdate(name=NAME), "cl-1")

    assert result.host is None


def test_readback_does_not_reuse_the_client_transaction_id():
    """The backend refuses a repeated clTRID, so the read-back would fail."""
    epp = client(CREATED, info())

    create_host(EppBackend(epp, EPP_NS_MAP), Host(name=NAME), "cl-1")

    assert "cl-1" in epp.sent[0]
    assert "cl-1" not in epp.sent[1]


def test_update_error_is_returned():
    assert isinstance(update_host(EppBackend(client(MISSING), EPP_NS_MAP), HostUpdate(name=NAME), "cl-1"), ErrorResponse)


def test_update_reads_back_under_the_new_name():
    epp = client(DONE, info())

    update_host(EppBackend(epp, EPP_NS_MAP), HostUpdate(name=NAME, new_name="ns2.example.example"), "cl-1")

    assert "ns2.example.example" in epp.sent[1]


def sent_update(epp) -> str:
    return epp.sent[1]


def test_replace_of_a_missing_host_is_an_error():
    epp = client(MISSING)

    assert isinstance(replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME), "cl-1"), ErrorResponse)
    assert len(epp.sent) == 1


def test_replace_adds_and_removes_addresses():
    epp = client(info(addresses=["192.0.2.1", "2001:db8::1"]), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, ipv4=["198.51.100.1"], ipv6=["2001:db8::1"]), "cl-1")

    xml = sent_update(epp)
    add = xml[xml.index("<host:add>"):xml.index("</host:add>")]
    rem = xml[xml.index("<host:rem>"):xml.index("</host:rem>")]
    assert "198.51.100.1" in add
    assert "192.0.2.1" in rem
    assert "2001:db8::1" not in xml


def test_replace_compares_addresses_by_value():
    epp = client(info(addresses=["2001:0DB8::0001"]), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, ipv6=["2001:db8::1"]), "cl-1")

    assert len(epp.sent) == 1


def test_replace_clears_what_the_request_omits():
    epp = client(info(statuses=["clientDeleteProhibited", "linked"], addresses=["192.0.2.1"]), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME), "cl-1")

    xml = sent_update(epp)
    rem = xml[xml.index("<host:rem>"):xml.index("</host:rem>")]
    assert "192.0.2.1" in rem
    assert 's="clientDeleteProhibited"' in rem
    assert "linked" not in xml


def test_replace_adds_a_status():
    epp = client(info(), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, status=["clientUpdateProhibited"]), "cl-1")

    assert 's="clientUpdateProhibited"' in sent_update(epp)


def test_replace_sends_the_reason_of_a_new_status():
    epp = client(info(), DONE, info())

    wanted = replacement(NAME, status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "x"})
    replace_host(EppBackend(epp, EPP_NS_MAP), wanted, "cl-1")

    assert ">x</host:status>" in sent_update(epp)


def status_blocks(xml):
    return xml[xml.index("<host:add>"):xml.index("</host:add>")], xml[xml.index("<host:rem>"):xml.index("</host:rem>")]


def test_replace_with_another_reason_replaces_the_status():
    epp = client(info(statuses=["clientDeleteProhibited"], reasons={"clientDeleteProhibited": "old"}), DONE, info())

    wanted = replacement(NAME, status=["clientDeleteProhibited"], status_reasons={"clientDeleteProhibited": "new"})
    replace_host(EppBackend(epp, EPP_NS_MAP), wanted, "cl-1")

    add, rem = status_blocks(sent_update(epp))
    assert ">new</host:status>" in add
    assert 's="clientDeleteProhibited"' in rem


def test_replace_that_omits_a_reason_clears_it():
    epp = client(info(statuses=["clientDeleteProhibited"], reasons={"clientDeleteProhibited": "old"}), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, status=["clientDeleteProhibited"]), "cl-1")

    add, rem = status_blocks(sent_update(epp))
    assert 's="clientDeleteProhibited"' in add
    assert 's="clientDeleteProhibited"' in rem


def test_replace_with_the_same_reason_changes_nothing():
    epp = client(info(statuses=["clientDeleteProhibited"], reasons={"clientDeleteProhibited": "x"}), DONE, info())

    wanted = replacement(NAME, status=["clientDeleteProhibited"], status_reasons={"clientDeleteProhibited": "x"})
    replace_host(EppBackend(epp, EPP_NS_MAP), wanted, "cl-1")

    assert len(epp.sent) == 1


def test_replace_with_another_name_renames():
    epp = client(info(), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement("ns2.example.example"), "cl-1")

    assert "<host:chg>" in sent_update(epp)
    assert "ns2.example.example" in epp.sent[2]


def test_replace_with_the_same_name_in_another_case_does_not_rename():
    epp = client(info(), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME.upper()), "cl-1")

    assert len(epp.sent) == 1


def test_replace_uses_the_client_transaction_id_for_the_update_only():
    epp = client(info(), DONE, info())

    replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, ipv4=["192.0.2.1"]), "cl-1")

    assert ["cl-1" in xml for xml in epp.sent] == [False, True, False]


def test_replace_error_from_the_update_is_returned():
    epp = client(info(), (False, "2304", epp_reply(2304)))

    assert isinstance(replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, ipv4=["192.0.2.1"]), "cl-1"), ErrorResponse)


def test_update_changes_default_to_empty():
    assert HostUpdateChanges() == HostUpdateChanges(ipv4=[], ipv6=[], status=[])


def never_called(host):
    raise AssertionError("the patch needs no current host")


def test_a_direct_patch_is_not_preceded_by_a_read():
    epp = client(DONE, info())
    update = HostUpdate(name=NAME, add=HostUpdateChanges(ipv4=["192.0.2.1"]))

    patch_host(EppBackend(epp, EPP_NS_MAP), NAME, update, never_called, "cl-1")

    assert "host:update" in epp.sent[0] and "host:info" in epp.sent[1]


def test_a_patch_needing_the_host_sends_the_difference():
    epp = client(info(addresses=["192.0.2.1"]), DONE, info())

    patch_host(EppBackend(epp, EPP_NS_MAP), NAME, None, lambda host: replacement(NAME, ipv4=["198.51.100.1"]), "cl-1")

    assert "host:info" in epp.sent[0]
    rem = sent_update(epp)[sent_update(epp).index("<host:rem>"):]
    assert "192.0.2.1" in rem
    assert "198.51.100.1" in sent_update(epp)


def test_only_the_update_carries_the_client_transaction_id():
    epp = client(info(), DONE, info())

    patch_host(EppBackend(epp, EPP_NS_MAP), NAME, None, lambda host: replacement(NAME, ipv4=["192.0.2.1"]), "cl-1")

    assert "cl-1" not in epp.sent[0]
    assert "cl-1" in epp.sent[1]
    assert "cl-1" not in epp.sent[2]


def test_a_patch_of_a_missing_host_is_an_error():
    epp = client(MISSING)

    assert isinstance(patch_host(EppBackend(epp, EPP_NS_MAP), NAME, None, never_called, "cl-1"), ErrorResponse)
    assert len(epp.sent) == 1


def test_a_patch_without_a_difference_sends_no_update():
    epp = client(info(addresses=["192.0.2.1"]))

    result = patch_host(EppBackend(epp, EPP_NS_MAP), NAME, None, lambda host: replacement(NAME, ipv4=["192.0.2.1"]), "cl-1")

    assert len(epp.sent) == 1
    assert result.host.ipv4 == ["192.0.2.1"]
    assert result.mutation.server_transaction_id == "sv-1"


def test_a_replacement_without_a_difference_sends_no_update():
    epp = client(info(addresses=["192.0.2.1"]))

    result = replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME, ipv4=["192.0.2.1"]), "cl-1")

    assert len(epp.sent) == 1
    assert result.host.ipv4 == ["192.0.2.1"]


@pytest.mark.parametrize("run", [
    lambda epp: replace_host(EppBackend(epp, EPP_NS_MAP), replacement(NAME), "cl-1"),
    lambda epp: patch_host(EppBackend(epp, EPP_NS_MAP), NAME, None, lambda host: replacement(NAME), "cl-1"),
])
def test_a_change_of_nothing_by_a_client_that_is_not_the_sponsor_is_refused(run):
    epp = client(info(), username="baz")

    result = run(epp)

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.AUTHORIZATION_ERROR
    assert len(epp.sent) == 1


def test_a_rename_alone_is_a_difference():
    epp = client(info(), DONE, info())

    patch_host(EppBackend(epp, EPP_NS_MAP), NAME, None, lambda host: replacement("ns2.example.example"), "cl-1")

    assert "ns2.example.example" in sent_update(epp)
