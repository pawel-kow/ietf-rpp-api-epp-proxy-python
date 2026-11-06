from epp_to_model_mapper.domains import create_domain_update_xml
from models import (
    DnsSec, DomainUpdate, DomainUpdateAdd, DomainUpdateChange, DomainUpdateRemove, DsData, HostAttr, NS,
)
from rpp_to_model_mapper import domain_patch


def update_xml(body):
    return create_domain_update_xml(domain_patch.rpp_to_model("foo.example", body), client_request_id="t")


def update_xml_of(domain_update):
    return create_domain_update_xml(domain_update, client_request_id="t")


def add_contact(label, contact_id):
    value = {"label": label, "object": {"@type": "contact", "id": contact_id}}
    return [{"op": "add", "path": "/contacts", "value": value}]


def test_added_contact_id_is_uppercased():
    assert '>FO-TEST1</domain:contact>' in update_xml(add_contact("tech", "fo-test1"))


def test_removed_contact_id_is_uppercased():
    match = {"label": "tech", "object": {"@type": "contact", "id": "fo-test1"}}

    assert '>FO-TEST1</domain:contact>' in update_xml([{"op": "remove", "path": "/contacts", "match": match}])


def test_registrant_id_is_uppercased():
    value = {"@type": "contact", "id": "fo-test1"}

    assert '<domain:registrant>FO-TEST1</domain:registrant>' in update_xml(
        [{"op": "replace", "path": "/registrant", "value": value}]
    )


def test_status_and_dnssec_are_updated():
    xml = update_xml_of(DomainUpdate(
        name="foo.example",
        add=DomainUpdateAdd(
            status=["clientHold"], status_reasons={"clientHold": "Pending"},
            dnsSEC=DnsSec(ds_data=[DsData(keyTag=1, algorithm=8, digestType=2, digest="AB")]),
        ),
        remove=DomainUpdateRemove(status=["clientUpdateProhibited"]),
    ))

    assert '<domain:status s="clientHold" lang="en">Pending</domain:status>' in xml
    assert '<domain:status s="clientUpdateProhibited" lang="en"/>' in xml
    assert "<secDNS:add>" in xml and "<secDNS:keyTag>1</secDNS:keyTag>" in xml
    assert "<secDNS:rem>" not in xml


def test_removed_host_attribute_names_its_addresses():
    ns = NS(host_objs=None, host_attrs=[HostAttr(id="ns1.foo.example", ipv4=["192.0.2.1"])])

    xml = update_xml_of(DomainUpdate(name="foo.example", remove=DomainUpdateRemove(ns=ns)))

    assert '<domain:hostAddr ip="v4">192.0.2.1</domain:hostAddr>' in xml


def test_auth_info_is_cleared_with_null():
    xml = update_xml_of(DomainUpdate(name="foo.example", change=DomainUpdateChange(clear_auth_info=True)))

    assert "<domain:null/>" in xml
