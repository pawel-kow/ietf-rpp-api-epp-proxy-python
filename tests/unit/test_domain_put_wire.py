import base64

import pytest

from core.session.session_pool import SessionPool
from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'

NAME = "foo.example"

AUTH = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": "application/rpp+json",
    "Content-Type": "application/rpp+json",
    "RPP-Cltrid": "cl-1",
}


def epp_reply(code):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def info(*hosts, sponsor="user"):
    ns = "".join(f"<domain:hostObj>{host}</domain:hostObj>" for host in hosts)
    reply = epp_reply(1000).replace("</result>", (
        f'</result><resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name><domain:roid>D1</domain:roid>'
        f'<domain:status s="ok"/><domain:ns>{ns}</domain:ns><domain:clID>{sponsor}</domain:clID><domain:crID>foo</domain:crID>'
        '<domain:crDate>2026-11-04T10:00:00.0Z</domain:crDate></domain:infData></resData>'
    ))
    return (True, "1000", reply)


DONE = (True, "1000", epp_reply(1000))
MISSING = (False, "2303", epp_reply(2303))
BODY = {"@type": "domainName", "nameservers": [{"@type": "host", "hostName": "ns1.foo.example"}]}


def put(*replies, body=BODY):
    def factory(username, password):
        return FakeEppClient(username, password, replies=replies)

    http = create_app(SessionPool(epp_backends(factory)), EPP_PROFILE).test_client()
    return http.put(f"/domainNames/{NAME}", json=body, headers=AUTH)


def test_put_is_a_200_with_the_domain():
    response = put(info("ns2.foo.example"), DONE, info("ns1.foo.example"))

    assert response.status_code == 200
    assert response.headers["RPP-Code"] == "01000"
    assert response.json()["nameservers"] == [{"@type": "host", "hostName": "ns1.foo.example"}]


def test_put_without_a_change_is_a_200_and_sends_no_update():
    response = put(info("ns1.foo.example"))

    assert response.status_code == 200
    assert response.json()["name"] == "FOO.EXAMPLE"


def test_put_without_a_change_by_another_client_than_the_sponsor_is_a_403():
    response = put(info("ns1.foo.example", sponsor="baz"))

    assert response.status_code == 403
    assert response.headers["RPP-Code"] == "02201"


def test_put_of_a_missing_domain_is_a_404():
    response = put(MISSING)

    assert response.status_code == 404
    assert response.headers["RPP-Code"] == "02303"


@pytest.mark.parametrize("member", ["name", "provMetadata", "expiryDate"])
def test_put_with_a_member_outside_the_update_is_a_400(member):
    response = put(body={**BODY, member: "x"})

    assert response.status_code == 400
    assert response.headers["RPP-Code"] == "02001"


def test_put_with_a_status_of_the_server_is_a_400():
    response = put(body={**BODY, "status": [{"@type": "domainStatus", "label": "ok"}]})

    assert response.status_code == 400


@pytest.mark.parametrize("readback", [MISSING, ConnectionError("gone")])
def test_failed_readback_after_put_is_a_202(readback):
    response = put(info("ns2.foo.example"), DONE, readback)

    assert response.status_code == 202
    assert response.text == ""
