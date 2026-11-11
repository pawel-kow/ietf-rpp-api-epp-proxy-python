import logging

from core.model.domain.dns_sec import DnsSec
from core.model.domain.domain_idn import DomainIdn
from core.model.domain.domains import Domain
from core.model.domain.ds_data import DsData
from registry_adapter.epp.commands.domain.create import create_domain_xml
from registry_adapter.epp.commands.domain.info import parse_domain_response
from registry_adapter.epp.idn_tables import IdnTables
from tests.helper.epp_ns_map import EPP_NS_MAP

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'

IDN_NS = 'xmlns:idn="urn:ietf:params:xml:ns:idn-1.0"'

TABLES = IdnTables({"latn-1.0": "de"})


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
    return create_domain_xml(Domain(name="xn--bcher-kva.example", **members), client_request_id="cl-1", ns_map=EPP_NS_MAP, idn_tables=TABLES)


def test_create_sends_the_table_of_the_lgr_and_uname_in_the_extension():
    xml = create_xml(idn=DomainIdn(lgr="latn-1.0", uname="bücher.example"))

    assert "<idn:data" in xml
    assert "<idn:table>de</idn:table>" in xml
    assert "<idn:uname>bücher.example</idn:uname>" in xml
    assert xml.index("</epp:create>") < xml.index("<idn:data") < xml.index("<epp:clTRID>")


def test_create_sends_the_table_of_the_lgr_alone():
    xml = create_xml(idn=DomainIdn(lgr="latn-1.0"))

    assert "<idn:table>de</idn:table>" in xml
    assert "uname" not in xml


def test_create_sends_dnssec_and_idn_together():
    ds = DsData(keyTag=1, algorithm=3, digestType=1, digest="AB")

    xml = create_xml(dnsSEC=DnsSec(ds_data=[ds]), idn=DomainIdn(lgr="latn-1.0"))

    assert "<secDNS:create" in xml
    assert "<idn:data" in xml


def test_create_has_no_extension_without_idn():
    assert "extension" not in create_xml()


def test_info_reads_the_lgr_of_the_table_and_uname():
    extension = (
        f'<extension><idn:data {IDN_NS}><idn:table>de</idn:table>'
        '<idn:uname>bücher.example</idn:uname></idn:data></extension>'
    )

    domain = parse_domain_response(info(extension), "cl-1", idn_tables=TABLES).payload

    assert domain.idn == DomainIdn(lgr="latn-1.0", uname="bücher.example")


def test_info_reads_the_lgr_of_the_table_alone():
    extension = f'<extension><idn:data {IDN_NS}><idn:table>de</idn:table></idn:data></extension>'

    assert parse_domain_response(info(extension), "cl-1", idn_tables=TABLES).payload.idn == DomainIdn(lgr="latn-1.0")


def test_info_without_the_extension_has_no_idn():
    assert parse_domain_response(info(), "cl-1", idn_tables=TABLES).payload.idn is None


def test_info_leaves_out_an_idn_whose_table_has_no_lgr(caplog):
    """Json §6.4 does not allow uName without lgr, so both are left out."""
    extension = (
        f'<extension><idn:data {IDN_NS}><idn:table>es</idn:table>'
        '<idn:uname>español.example</idn:uname></idn:data></extension>'
    )

    with caplog.at_level(logging.WARNING):
        domain = parse_domain_response(info(extension), "cl-1", idn_tables=TABLES).payload

    assert domain.idn is None
    assert "es" in caplog.text
