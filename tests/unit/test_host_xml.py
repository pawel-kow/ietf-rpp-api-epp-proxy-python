from models import Host, HostUpdate, HostUpdateChanges
from epp_to_model_mapper import (
    create_host_update_xml, create_host_xml, delete_host_xml, host_check_xml, info_host_xml,
    parse_host_check_response, parse_host_create_response, parse_host_delete_response, parse_host_response,
    parse_host_update_response,
)

HOST_NS = 'xmlns:host="urn:ietf:params:xml:ns:host-1.0"'


def reply(res_data=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="1000"><msg>Command completed successfully</msg></result>{res_data}'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def test_check():
    xml = host_check_xml("ns1.example.example", client_request_id="cl-1")

    assert "<host:check" in xml
    assert "<host:name>ns1.example.example</host:name>" in xml
    assert "<clTRID>cl-1</clTRID>" in xml or "<epp:clTRID>cl-1</epp:clTRID>" in xml


def test_info():
    assert "<host:info" in info_host_xml("ns1.example.example")


def test_delete():
    assert "<host:delete" in delete_host_xml("ns1.example.example")


def test_create_without_addresses():
    xml = create_host_xml(Host(name="ns1.example.example"))

    assert "<host:create" in xml
    assert "host:addr" not in xml


def test_create_with_addresses():
    xml = create_host_xml(Host(name="ns1.example.example", ipv4=["192.0.2.1"], ipv6=["2001:db8::1"]))

    assert '<host:addr ip="v4">192.0.2.1</host:addr>' in xml
    assert '<host:addr ip="v6">2001:db8::1</host:addr>' in xml


def test_update_add_and_remove():
    xml = create_host_update_xml(HostUpdate(
        name="ns1.example.example",
        add=HostUpdateChanges(ipv4=["192.0.2.2"], status=["clientUpdateProhibited"]),
        remove=HostUpdateChanges(ipv6=["2001:db8::1"], status=["clientDeleteProhibited"]),
    ))

    add = xml[xml.index("<host:add>"):xml.index("</host:add>")]
    rem = xml[xml.index("<host:rem>"):xml.index("</host:rem>")]
    assert '<host:addr ip="v4">192.0.2.2</host:addr>' in add
    assert 's="clientUpdateProhibited"' in add
    assert '<host:addr ip="v6">2001:db8::1</host:addr>' in rem
    assert 's="clientDeleteProhibited"' in rem
    assert "host:chg" not in xml


def test_update_sends_the_status_reason():
    xml = create_host_update_xml(HostUpdate(
        name="ns1.example.example",
        add=HostUpdateChanges(status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "x & y"}),
    ))

    assert ">x &amp; y</host:status>" in xml


def test_update_rename():
    xml = create_host_update_xml(HostUpdate(name="ns1.example.example", new_name="ns2.example.example"))

    assert "<host:chg>" in xml
    assert "<host:name>ns2.example.example</host:name>" in xml
    assert "host:add" not in xml
    assert "host:rem" not in xml


INFO = (
    f'<resData><host:infData {HOST_NS}><host:name>NS1.EXAMPLE.EXAMPLE</host:name><host:roid>H1-EX</host:roid>'
    '<host:status s="ok"/><host:status s="linked"/>{addresses}<host:clID>foo</host:clID><host:crID>bar</host:crID>'
    '<host:crDate>2026-11-04T10:00:00.0Z</host:crDate><host:upID>foo</host:upID>'
    '<host:upDate>2026-11-05T10:00:00.0Z</host:upDate><host:trDate>2026-11-06T10:00:00.0Z</host:trDate>'
    '</host:infData></resData>'
)


def parsed_info(addresses=""):
    return parse_host_response(reply(INFO.format(addresses=addresses)), "cl-1")


def test_parse_info():
    response = parsed_info()

    assert response.host.name == "NS1.EXAMPLE.EXAMPLE"
    assert response.host.status == ["ok", "linked"]
    assert response.host.clID == "foo"
    assert response.host.crID == "bar"
    assert response.host.crDate == "2026-11-04T10:00:00.000000Z"
    assert response.host.upDate == "2026-11-05T10:00:00.000000Z"
    assert response.host.trDate == "2026-11-06T10:00:00.000000Z"
    assert response.server_transaction_id == "sv-1"


def test_parse_info_addresses():
    host = parsed_info('<host:addr ip="v4">192.0.2.1</host:addr><host:addr ip="v6">2001:db8::1</host:addr>').host

    assert host.ipv4 == ["192.0.2.1"]
    assert host.ipv6 == ["2001:db8::1"]


def test_parse_info_does_not_rely_on_the_ip_attribute():
    """The backend sends ip="v" and ip="vv4"."""
    host = parsed_info('<host:addr ip="v">192.0.2.1</host:addr><host:addr ip="vv4">2001:db8::1</host:addr>').host

    assert host.ipv4 == ["192.0.2.1"]
    assert host.ipv6 == ["2001:db8::1"]


def test_parse_info_status_reason():
    xml = reply(INFO.format(addresses="")).replace('<host:status s="ok"/>', '<host:status s="ok">Checked</host:status>')

    assert parse_host_response(xml, "cl-1").host.status_reasons == {"ok": "Checked"}


def test_parse_info_status_text_equal_to_the_label_is_no_reason():
    xml = reply(INFO.format(addresses="")).replace('<host:status s="ok"/>', '<host:status s="ok">ok</host:status>')

    assert parse_host_response(xml, "cl-1").host.status_reasons == {}


def test_parse_create():
    res_data = (
        f'<resData><host:creData {HOST_NS}><host:name>NS1.EXAMPLE.EXAMPLE</host:name>'
        '<host:crDate>2026-11-04T10:00:00.0Z</host:crDate></host:creData></resData>'
    )

    host = parse_host_create_response(reply(res_data), "cl-1").host

    assert host.name == "NS1.EXAMPLE.EXAMPLE"
    assert host.crDate == "2026-11-04T10:00:00.000000Z"


def check_reply(name, avail, reason=""):
    return reply(
        f'<resData><host:chkData {HOST_NS}><host:cd><host:name avail="{avail}">{name}</host:name>{reason}'
        '</host:cd></host:chkData></resData>'
    )


def test_parse_check_available():
    response = parse_host_check_response(check_reply("NS1.EXAMPLE.EXAMPLE", 1), "ns1.example.example", "cl-1")

    assert response.available is True
    assert response.reason is None
    assert response.host_name == "ns1.example.example"


def test_parse_check_taken():
    reason = "<host:reason>In use</host:reason>"

    response = parse_host_check_response(check_reply("ns1.example.example", 0, reason), "NS1.EXAMPLE.EXAMPLE", "cl-1")

    assert response.available is False
    assert response.reason == "In use"


def test_parse_update_and_delete():
    assert parse_host_update_response(reply(), "cl-1").server_transaction_id == "sv-1"
    assert parse_host_delete_response(reply(), "cl-1").server_transaction_id == "sv-1"


def test_no_client_transaction_id_is_not_reported():
    assert parse_host_update_response(reply(), None).client_transaction_id is None
