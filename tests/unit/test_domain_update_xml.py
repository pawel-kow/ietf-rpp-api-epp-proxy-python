from epp_to_model_mapper.domains import create_domain_update_xml
from rpp_to_model_mapper import rpp_to_domain_update


def update_xml(body):
    return create_domain_update_xml(rpp_to_domain_update("foo.example", body), client_request_id="t")


def contacts(contact_type, contact_id):
    return {"contacts": [{"type": contact_type, "object": {"id": contact_id}}]}


def test_added_contact_id_is_uppercased():
    assert '>FO-TEST1</domain:contact>' in update_xml({"add": contacts("tech", "fo-test1")})


def test_removed_contact_id_is_uppercased():
    assert '>FO-TEST1</domain:contact>' in update_xml({"remove": contacts("tech", "fo-test1")})


def test_registrant_id_is_uppercased():
    assert '<domain:registrant>FO-TEST1</domain:registrant>' in update_xml({"add": contacts("registrant", "fo-test1")})
