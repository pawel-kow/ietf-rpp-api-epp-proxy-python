"""`includeElements` on the wire: the onDemand `authInfo` of a domain is shown when included, and a full update
treats it as part of the representation only then (see spec-issues.md)."""
import base64

from eppclient.epp_profile import EPP_PROFILE
from app import create_app
from controller.session_authenticator import SessionAuthenticator
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

DOMAIN_NS = 'xmlns:domain="urn:ietf:params:xml:ns:domain-1.0"'
URL = "/domainNames/foo.example"
AUTH = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": "application/rpp+json",
    "Content-Type": "application/rpp+json",
    "RPP-Cltrid": "cl-1",
}
PASSWORD = {"@type": "authInfo", "method": "authinfo", "authdata": "NewSecret1!x"}
BODY = {"@type": "domainName", "nameservers": [{"@type": "host", "hostName": "ns1.foo.example"}]}


def epp_reply(code, res_data=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


INFO = (True, "1000", epp_reply(1000, (
    f'<resData><domain:infData {DOMAIN_NS}><domain:name>FOO.EXAMPLE</domain:name><domain:roid>D1</domain:roid>'
    '<domain:status s="ok"/><domain:ns><domain:hostObj>ns1.foo.example</domain:hostObj></domain:ns>'
    '<domain:clID>user</domain:clID><domain:crDate>2026-11-04T10:00:00.0Z</domain:crDate>'
    '<domain:authInfo><domain:pw>Secret1!x</domain:pw></domain:authInfo></domain:infData></resData>'
)))
DONE = (True, "1000", epp_reply(1000))


def http(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, replies=replies))
        return clients[-1]

    return create_app(SessionAuthenticator(epp_backends(factory)), EPP_PROFILE).test_client(), clients


def test_a_read_leaves_out_auth_info_unless_it_is_included():
    client, _ = http(INFO, INFO)

    assert "authInfo" not in client.get(URL, headers=AUTH).json()
    assert client.get(f"{URL}?includeElements=authInfo", headers=AUTH).json()["authInfo"]["authdata"] == "Secret1!x"


def test_included_elements_are_repeated_parameters():
    client, _ = http(INFO)

    response = client.get(f"{URL}?includeElements=status&includeElements=authInfo", headers=AUTH)

    assert response.status_code == 200 and "authInfo" in response.json()


def test_an_unknown_element_is_a_400_before_any_epp_command():
    client, clients = http(INFO)

    response = client.get(f"{URL}?includeElements=authInfo,status", headers=AUTH)

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02001"
    assert not any(c.sent for c in clients)


def test_a_full_update_with_auth_info_it_does_not_include_is_a_400():
    client, _ = http(INFO)

    response = client.put(URL, json={**BODY, "authInfo": PASSWORD}, headers=AUTH)

    assert response.status_code == 400 and "includeElements=authInfo" in response.json()["detail"]


def test_a_full_update_including_auth_info_and_omitting_it_clears_it():
    client, clients = http(INFO, DONE, INFO)

    response = client.put(f"{URL}?includeElements=authInfo", json=BODY, headers=AUTH)

    assert response.status_code == 200 and response.json()["authInfo"]["authdata"] == "Secret1!x"
    update = next(m for c in clients for m in c.sent if "<domain:update>" in m)
    assert "<domain:null/>" in update


def test_a_full_update_without_auth_info_leaves_it_alone():
    client, clients = http(INFO)

    response = client.put(URL, json=BODY, headers=AUTH)

    assert response.status_code == 200 and "authInfo" not in response.json()
    assert not any("<domain:update>" in m for c in clients for m in c.sent)
