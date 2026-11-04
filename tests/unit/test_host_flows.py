from flows import create_host, replace_host, update_host
from models import ErrorResponse, Host, HostUpdate, HostUpdateChanges
from tests.helper.fake_epp_client import FakeEppClient

HOST_NS = 'xmlns:host="urn:ietf:params:xml:ns:host-1.0"'
NAME = "ns1.example.example"


def epp_reply(code, res_data=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def info(statuses=("ok",), addresses=()):
    status = "".join(f'<host:status s="{s}"/>' for s in statuses)
    addr = "".join(f'<host:addr ip="v">{a}</host:addr>' for a in addresses)
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


def client(*replies):
    return FakeEppClient("u", "p", replies=replies)


def test_create_reads_the_host_back():
    result = create_host(client(CREATED, info()), Host(name=NAME), "cl-1")

    assert result.host.status == ["ok"]
    assert result.mutation.server_transaction_id == "sv-1"


def test_create_error_is_returned():
    assert isinstance(create_host(client(EXISTS), Host(name=NAME), "cl-1"), ErrorResponse)


def test_failed_readback_has_no_host():
    result = create_host(client(CREATED, MISSING), Host(name=NAME), "cl-1")

    assert result.host is None
    assert result.mutation.server_transaction_id == "sv-1"


def test_exception_during_readback_has_no_host():
    result = update_host(client(DONE, ConnectionError("gone")), HostUpdate(name=NAME), "cl-1")

    assert result.host is None


def test_readback_does_not_reuse_the_client_transaction_id():
    """The backend hangs on a repeated clTRID."""
    epp = client(CREATED, info())

    create_host(epp, Host(name=NAME), "cl-1")

    assert "cl-1" in epp.sent[0]
    assert "cl-1" not in epp.sent[1]


def test_update_error_is_returned():
    assert isinstance(update_host(client(MISSING), HostUpdate(name=NAME), "cl-1"), ErrorResponse)


def test_update_reads_back_under_the_new_name():
    epp = client(DONE, info())

    update_host(epp, HostUpdate(name=NAME, new_name="ns2.example.example"), "cl-1")

    assert "ns2.example.example" in epp.sent[1]


def sent_update(epp) -> str:
    return epp.sent[1]


def test_replace_of_a_missing_host_is_an_error():
    epp = client(MISSING)

    assert isinstance(replace_host(epp, NAME, Host(name=NAME), "cl-1"), ErrorResponse)
    assert len(epp.sent) == 1


def test_replace_adds_and_removes_addresses():
    epp = client(info(addresses=["192.0.2.1", "2001:db8::1"]), DONE, info())

    replace_host(epp, NAME, Host(name=NAME, ipv4=["198.51.100.1"], ipv6=["2001:db8::1"]), "cl-1")

    xml = sent_update(epp)
    add = xml[xml.index("<host:add>"):xml.index("</host:add>")]
    rem = xml[xml.index("<host:rem>"):xml.index("</host:rem>")]
    assert "198.51.100.1" in add
    assert "192.0.2.1" in rem
    assert "2001:db8::1" not in xml


def test_replace_compares_addresses_by_value():
    epp = client(info(addresses=["2001:0DB8::0001"]), DONE, info())

    replace_host(epp, NAME, Host(name=NAME, ipv6=["2001:db8::1"]), "cl-1")

    assert "host:addr" not in sent_update(epp)


def test_replace_clears_what_the_request_omits():
    epp = client(info(statuses=["clientDeleteProhibited", "linked"], addresses=["192.0.2.1"]), DONE, info())

    replace_host(epp, NAME, Host(name=NAME), "cl-1")

    xml = sent_update(epp)
    rem = xml[xml.index("<host:rem>"):xml.index("</host:rem>")]
    assert "192.0.2.1" in rem
    assert 's="clientDeleteProhibited"' in rem
    assert "linked" not in xml


def test_replace_adds_a_status():
    epp = client(info(), DONE, info())

    replace_host(epp, NAME, Host(name=NAME, status=["clientUpdateProhibited"]), "cl-1")

    assert 's="clientUpdateProhibited"' in sent_update(epp)


def test_replace_with_another_name_renames():
    epp = client(info(), DONE, info())

    replace_host(epp, NAME, Host(name="ns2.example.example"), "cl-1")

    assert "<host:chg>" in sent_update(epp)
    assert "ns2.example.example" in epp.sent[2]


def test_replace_with_the_same_name_in_another_case_does_not_rename():
    epp = client(info(), DONE, info())

    replace_host(epp, NAME, Host(name=NAME.upper()), "cl-1")

    assert "host:chg" not in sent_update(epp)


def test_replace_uses_the_client_transaction_id_for_the_update_only():
    epp = client(info(), DONE, info())

    replace_host(epp, NAME, Host(name=NAME), "cl-1")

    assert ["cl-1" in xml for xml in epp.sent] == [False, True, False]


def test_replace_error_from_the_update_is_returned():
    epp = client(info(), (False, "2304", epp_reply(2304)))

    assert isinstance(replace_host(epp, NAME, Host(name=NAME, ipv4=["192.0.2.1"]), "cl-1"), ErrorResponse)


def test_update_changes_default_to_empty():
    assert HostUpdateChanges() == HostUpdateChanges(ipv4=[], ipv6=[], status=[])
