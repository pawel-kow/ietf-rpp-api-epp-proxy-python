from registry_adapter.epp.commands.domain.domain_xml import create_domain_xml, parse_domain_response
from models import DnsSec, Domain, DomainIdn, DsData
from tests.helper.epp_ns_map import EPP_NS_MAP

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'
IDN_NS = 'xmlns:idn="urn:ietf:params:xml:ns:idn-1.0"'


def info(extension=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        '<result code="1000"><msg>Command completed successfully</msg></result>'
        f'<resData><domain:infData {DOMAIN_NS}><domain:name>XN--BCHER-KVA.EXAMPLE</domain:name>'
        '<domain:roid>D1-EX</domain:roid><domain:status s="ok"/>'
        '<domain:clID>foo</domain:clID></domain:infData></resData>'
        f'{extension}<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def create_xml(**members):
    return create_domain_xml(Domain(name="xn--bcher-kva.example", **members), client_request_id="cl-1", ns_map=EPP_NS_MAP)


def test_create_sends_table_and_uname_in_the_extension():
    xml = create_xml(idn=DomainIdn(table="de", uname="bücher.example"))

    assert "<idn:data" in xml
    assert "<idn:table>de</idn:table>" in xml
    assert "<idn:uname>bücher.example</idn:uname>" in xml
    assert xml.index("</epp:create>") < xml.index("<idn:data") < xml.index("<epp:clTRID>")


def test_create_sends_the_table_alone():
    xml = create_xml(idn=DomainIdn(table="de"))

    assert "<idn:table>de</idn:table>" in xml
    assert "uname" not in xml


def test_create_sends_dnssec_and_idn_together():
    ds = DsData(keyTag=1, algorithm=3, digestType=1, digest="AB")

    xml = create_xml(dnsSEC=DnsSec(ds_data=[ds]), idn=DomainIdn(table="de"))

    assert "<secDNS:create" in xml
    assert "<idn:data" in xml


def test_create_has_no_extension_without_idn():
    assert "extension" not in create_xml()


def test_info_reads_table_and_uname():
    extension = (
        f'<extension><idn:data {IDN_NS}><idn:table>de</idn:table>'
        '<idn:uname>bücher.example</idn:uname></idn:data></extension>'
    )

    domain = parse_domain_response(info(extension), "cl-1").domain

    assert domain.idn == DomainIdn(table="de", uname="bücher.example")


def test_info_reads_the_table_alone():
    extension = f'<extension><idn:data {IDN_NS}><idn:table>de</idn:table></idn:data></extension>'

    assert parse_domain_response(info(extension), "cl-1").domain.idn == DomainIdn(table="de")


def test_info_without_the_extension_has_no_idn():
    assert parse_domain_response(info(), "cl-1").domain.idn is None
