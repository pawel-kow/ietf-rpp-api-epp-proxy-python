from epp_to_model_mapper.domains import create_domain_update_xml
from rpp_to_model_mapper import rpp_to_domain_update


def update_xml(body):
    return create_domain_update_xml(rpp_to_domain_update("foo.example", body), client_request_id="t")


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
