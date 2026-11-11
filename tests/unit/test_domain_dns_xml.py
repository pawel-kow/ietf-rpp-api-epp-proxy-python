from registry_adapter.epp.commands.domain.domain_xml import create_domain_xml, parse_domain_response
from core.model.domain.dns_sec import DnsSec
from core.model.domain.domains import Domain, HostAttr, NS
from core.model.domain.ds_data import DsData
from core.model.domain.key_data import KeyData
from registry_adapter.epp.idn_tables import IdnTables
from tests.helper.epp_ns_map import EPP_NS_MAP

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'
SEC_DNS_NS = 'xmlns:secDNS="urn:ietf:params:xml:ns:secDNS-1.1"'
DS = DsData(keyTag=12345, algorithm=3, digestType=1, digest="49FD46E6C4B45C55D4AC")
KEY = KeyData(flags=257, protocol=3, algorithm=8, publicKey="AQPJ////4Q==")


def info(members="", extension=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        '<result code="1000"><msg>Command completed successfully</msg></result>'
        f'<resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name>'
        f'<domain:roid>D1-EX</domain:roid><domain:status s="ok"/>{members}'
        '<domain:clID>foo</domain:clID></domain:infData></resData>'
        f'{extension}<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def create_xml(**members):
    return create_domain_xml(Domain(name="foo.example", **members), client_request_id="cl-1", ns_map=EPP_NS_MAP, idn_tables=IdnTables())


def test_create_has_no_extension_without_dnssec():
    assert "extension" not in create_xml()


def test_create_sends_ds_data_in_the_extension():
    xml = create_xml(dnsSEC=DnsSec(ds_data=[DS]))

    assert "<secDNS:create" in xml
    assert "<secDNS:keyTag>12345</secDNS:keyTag>" in xml
    assert "<secDNS:alg>3</secDNS:alg>" in xml
    assert "<secDNS:digestType>1</secDNS:digestType>" in xml
    assert "<secDNS:digest>49FD46E6C4B45C55D4AC</secDNS:digest>" in xml
    assert xml.index("</epp:create>") < xml.index("<secDNS:create") < xml.index("<epp:clTRID>")


def test_create_sends_key_data_in_the_extension():
    xml = create_xml(dnsSEC=DnsSec(key_data=[KEY]))

    assert "<secDNS:flags>257</secDNS:flags>" in xml
    assert "<secDNS:protocol>3</secDNS:protocol>" in xml
    assert "<secDNS:alg>8</secDNS:alg>" in xml
    assert "<secDNS:pubKey>AQPJ////4Q==</secDNS:pubKey>" in xml


def test_create_sends_host_attributes():
    xml = create_xml(ns=NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"])]))

    assert "<domain:hostName>ns1.foo.example</domain:hostName>" in xml
    assert '192.0.2.1</domain:hostAddr>' in xml


def test_info_reads_the_repository_and_update_client():
    domain = parse_domain_response(info("<domain:upID>ClientY</domain:upID>"), "cl-1", idn_tables=IdnTables()).domain

    assert domain.roid == "D1-EX"
    assert domain.upID == "ClientY"


def test_info_reads_subordinate_hosts():
    members = "<domain:host>NS1.FOO.EXAMPLE</domain:host><domain:host>NS2.FOO.EXAMPLE</domain:host>"

    assert parse_domain_response(info(members), "cl-1", idn_tables=IdnTables()).domain.subordinateHosts == [
        "NS1.FOO.EXAMPLE", "NS2.FOO.EXAMPLE",
    ]


def test_info_without_subordinate_hosts():
    assert parse_domain_response(info(), "cl-1", idn_tables=IdnTables()).domain.subordinateHosts is None


def test_info_reads_ds_data():
    extension = (
        f'<extension><secDNS:infData {SEC_DNS_NS}><secDNS:dsData><secDNS:keyTag>12345</secDNS:keyTag>'
        '<secDNS:alg>3</secDNS:alg><secDNS:digestType>1</secDNS:digestType>'
        '<secDNS:digest>49fd46e6c4b45c55d4ac</secDNS:digest></secDNS:dsData></secDNS:infData></extension>'
    )

    assert parse_domain_response(info(extension=extension), "cl-1", idn_tables=IdnTables()).domain.dnsSEC == DnsSec(ds_data=[DS])


def test_info_reads_key_data():
    extension = (
        f'<extension><secDNS:infData {SEC_DNS_NS}><secDNS:keyData><secDNS:flags>257</secDNS:flags>'
        '<secDNS:protocol>3</secDNS:protocol><secDNS:alg>8</secDNS:alg>'
        '<secDNS:pubKey>AQPJ////4Q==</secDNS:pubKey></secDNS:keyData></secDNS:infData></extension>'
    )

    assert parse_domain_response(info(extension=extension), "cl-1", idn_tables=IdnTables()).domain.dnsSEC == DnsSec(key_data=[KEY])


def test_info_ignores_other_extensions():
    extension = (
        '<extension><rgp:infData xmlns:rgp="urn:ietf:params:xml:ns:rgp-1.0">'
        '<rgp:rgpStatus s="addPeriod"/></rgp:infData></extension>'
    )

    assert parse_domain_response(info(extension=extension), "cl-1", idn_tables=IdnTables()).domain.dnsSEC is None


def test_info_reads_the_status_reason_and_not_the_repeated_label():
    xml = info().replace(
        '<domain:status s="ok"/>',
        '<domain:status s="clientHold">Unpaid</domain:status><domain:status s="clientUpdateProhibited">clientUpdateProhibited</domain:status>',
    )

    assert parse_domain_response(xml, "cl-1", idn_tables=IdnTables()).domain.status_reasons == {"clientHold": "Unpaid"}
