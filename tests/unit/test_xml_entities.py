import base64

import pytest

from core.session.session_pool import SessionPool
from registry_adapter.common.xmlsafe.xml_helper import decode_xml
from registry_adapter.epp.commands.message.poll import parse_poll_response
from registry_adapter.epp.commands.shared.epp_core import get_epp_error_response
from tests.helper.profiles import EPP_PROFILE
from registry_adapter.epp.xml.codec import str_to_epp
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

SECRET = "SECRET-FILE-CONTENT-8f3a"

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": "application/rpp+json",
    "RPP-Cltrid": "xxe-cl-1",
}


@pytest.fixture
def secret_file(tmp_path):
    path = tmp_path / "secret.txt"
    path.write_text(SECRET)
    return path


def hostile(secret_file, body, code="1301"):
    """An EPP reply whose DOCTYPE declares an external entity that reads a local file."""
    return (
        f'<?xml version="1.0"?><!DOCTYPE epp [<!ENTITY x SYSTEM "file://{secret_file}">]>'
        f'<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="{code}"><msg>Message &x;</msg></result>'
        f'{body}<trID><clTRID>xxe-cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


MSG = '<msgQ count="1" id="5"><qDate>2026-11-05T16:49:34.0Z</qDate><msg>A&x;B</msg></msgQ>'


def test_the_typed_parser_refuses_a_doctype(secret_file):
    with pytest.raises(ValueError) as raised:
        str_to_epp(hostile(secret_file, MSG))
    assert SECRET not in str(raised.value)


def test_decode_xml_does_not_resolve_entities(secret_file):
    root = decode_xml(hostile(secret_file, MSG))
    assert SECRET not in "".join(root.itertext())


def test_error_replies_do_not_resolve_entities(secret_file):
    resp = get_epp_error_response(hostile(secret_file, "", "2303"), "xxe-cl-1")
    assert SECRET not in resp.msg


def test_a_message_with_an_entity_reaches_the_raw_path_and_does_not_leak(secret_file):
    resp = parse_poll_response(hostile(secret_file, MSG), "xxe-cl-1")
    assert resp.payload.message.id == "5"
    assert SECRET not in repr(resp)


def client(*replies):
    def factory(username, password):
        return FakeEppClient(username, password, replies=list(replies))

    return create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client()


def test_a_message_with_an_entity_does_not_leak_through_the_api(secret_file):
    response = client((True, "1301", hostile(secret_file, MSG))).get("/messages", headers=HEADERS)
    assert response.status_code == 200
    assert SECRET not in response.text
    assert SECRET not in str(response.headers)


def test_an_ordinary_command_fails_cleanly_on_a_doctype(secret_file):
    reply = hostile(secret_file, "", "1000")
    response = client((True, "1000", reply)).get("/domainNames/foo.example", headers=HEADERS)
    assert response.status_code == 500
    assert SECRET not in response.text
    assert SECRET not in str(response.headers)
