"""The app composed for RRI: the refusals RRI_PROFILE drives, before any command, and a round trip."""
import base64
from types import SimpleNamespace

import pytest

from core.session.session_pool import SessionPool
from tests.helper.profiles import RRI_PROFILE
from rpp.http.app import create_app
from tests.helper.fake_rri_client import FakeRriClient, reply, rri_backends
from tests.unit.test_rri_adapter import DOMAIN_INFO, NAME

MEDIA_TYPE = "application/rpp+json"

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"DENIC-1000022-RRI:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "cl-1",
}

BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}

DISCOVERY = SimpleNamespace(rpp_base_url="https://rpp.example", rpp_tlds=["de"], rpp_environment_name="test",
                            rpp_environment_status="test")


def setup(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeRriClient(username, password, replies=list(replies)))
        return clients[-1]

    return create_app(SessionPool(rri_backends(factory)), RRI_PROFILE, discovery_settings=DISCOVERY).test_client(), clients


def assert_refused(response, clients, code="02102"):
    assert response.status_code == 501, response.text
    assert response.headers["RPP-Code"] == code
    assert all(not client.sent for client in clients)


CONTACT = {"@type": "contact", "id": "DENIC-1000022-X", "contactInfo": {
    "@type": "Card", "version": "2.0", "kind": "individual", "name": {"full": "Erika Mustermann"},
    "addresses": {"addr": {"components": [{"kind": "locality", "value": "Frankfurt"}], "countryCode": "DE"}},
    "emails": {"email": {"address": "erika@example.com"}}}}


@pytest.mark.parametrize("body", [
    {"@type": "domainName", "name": NAME, "nameservers": [{"@type": "host", "hostName": "ns1.example.com"}]},
    {"@type": "domainName", "name": NAME, "contacts": [{"label": "admin", "object": {"@type": "contact", "id": "C"}}]},
    {"@type": "domainName", "name": NAME, "dns": {"@type": "dnsData", "records": [
        {"@type": "dnsRecord", "name": "@", "type": "ds",
         "rdata": {"keyTag": "1", "algorithm": "8", "digestType": "2", "digest": "AB"}}]}},
])
def test_domain_input_rri_cannot_hold_is_refused(body):
    client, clients = setup()

    assert_refused(client.post("/domainNames", json=body, headers=BODY_HEADERS), clients)


def test_a_contact_fax_is_refused():
    client, clients = setup()
    body = {**CONTACT, "contactInfo": {**CONTACT["contactInfo"], "phones": {
        "fax": {"number": "tel:+49.6912345678", "features": {"fax": True}}}}}

    assert_refused(client.post("/contacts", json=body, headers=BODY_HEADERS), clients)


def test_a_client_status_is_refused():
    client, clients = setup(DOMAIN_INFO)

    response = client.patch(f"/domainNames/{NAME}", json=[
        {"op": "add", "path": "/status", "value": {"@type": "domainStatus", "label": "clientHold"}}],
        headers=BODY_HEADERS)

    assert response.status_code == 501 and response.headers["RPP-Code"] == "02102"


@pytest.mark.parametrize("method, url", [
    ("GET", "/hosts/ns1.example.de"),
    ("POST", f"/domainNames/{NAME}/processes/renewProcesses"),
    ("DELETE", "/contacts/DENIC-1000022-X"),
])
def test_commands_rri_lacks_answer_501(method, url):
    client, clients = setup()

    body = {"@type": "renewProcess"} if "renew" in url else None
    response = client.request(method, url, json=body, headers=BODY_HEADERS if body else HEADERS)

    assert_refused(response, clients, "02101")


def test_a_domain_is_read_with_its_records():
    client, _ = setup(DOMAIN_INFO)

    response = client.get(f"/domainNames/{NAME}", headers=HEADERS)

    assert response.status_code == 200
    body = response.json()
    assert body["registrant"]["id"] == "DENIC-1000022-HOLDER"
    assert {"label": "abuse", "object": {"@type": "contact", "id": "DENIC-1000022-GENREQ"}} in body["contacts"]
    assert {"@type": "dnsRecord", "name": "www.rpp-exp-caa50f65.de.", "type": "aaaa",
            "rdata": {"address": "2001:db8::1"}} in body["dns"]["records"]
    assert body["provMetadata"]["spClientId"] == "DENIC-1000022"
    assert response.headers["RPP-Cltrid"] == "cl-1"


def test_a_refusal_names_the_denic_code():
    client, _ = setup(reply("failed", messages='<tr:message level="error" code="63300022003"><tr:text>'
                                                'This domain is administered by another provider</tr:text>'
                                                '</tr:message>'))

    response = client.delete(f"/domainNames/{NAME}", headers=HEADERS)

    assert response.status_code == 403
    assert response.json()["detail"].startswith("63300022003 ")


def test_discovery_states_the_objects_of_rri():
    client, _ = setup()

    response = client.get("/.well-known/rpp", headers={"Accept": MEDIA_TYPE, "RPP-Cltrid": "cl-1"})

    assert response.status_code == 200, response.text
    assert response.json()["objects"] == ["domainName", "contact"]


def test_a_deleted_domain_reads_with_a_placeholder_sponsor():
    client, _ = setup(reply(data=('<domain:infoData xmlns:domain="http://registry.denic.de/domain/5.0">'
                                  f'<domain:handle>{NAME}</domain:handle><domain:ace>{NAME}</domain:ace>'
                                  '<domain:status>redemptionPeriod</domain:status>'
                                  '<domain:changed>2026-11-12T01:20:34+01:00</domain:changed></domain:infoData>')))

    response = client.get(f"/domainNames/{NAME}", headers=HEADERS)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == [{"@type": "domainStatus", "label": "pendingDelete"}]
    assert body["provMetadata"]["spClientId"] == "unknown"


def test_a_create_applied_in_part_is_accepted_without_a_read_back():
    client, clients = setup(reply(stid="sv-create"),
                            reply("failed", messages='<tr:message level="error" code="63391068704"><tr:text>AuthInfo1 '
                                                     'already exists</tr:text></tr:message>'))

    response = client.post("/domainNames", json={
        "@type": "domainName", "name": NAME, "registrant": {"@type": "contact", "id": "DENIC-1000022-HOLDER"},
        "dns": {"@type": "dnsData", "records": [{"@type": "dnsRecord", "name": "@", "type": "a",
                                                 "rdata": {"address": "192.0.2.10"}}]},
        "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "Abc2345678"}}, headers=BODY_HEADERS)

    assert response.status_code == 202, response.text
    assert response.headers["RPP-Svtrid"] == "sv-create"
    assert len(clients[0].sent) == 2


TRANSFER_URL = f"/domainNames/{NAME}/processes/transferProcesses"

TRANSFER = {
    "@type": "domainTransferProcess",
    "registrant": {"@type": "contact", "id": "DENIC-1000022-HOLDER"},
    "dns": {"@type": "dnsData", "records": [
        {"@type": "dnsRecord", "name": "@", "type": "a", "rdata": {"address": "192.0.2.10"}}]},
}

AUTHORIZATION = {"RPP-Authorization": "authinfo value=" + base64.b64encode(b"Abc2345678").decode()}


def test_a_transfer_with_the_rri_extension_completes_at_once():
    client, clients = setup(reply(stid="sv-chprov"))

    response = client.post(TRANSFER_URL, json=TRANSFER, headers={**BODY_HEADERS, **AUTHORIZATION})

    assert response.status_code == 200, response.text
    assert "Location" not in response.headers
    assert response.headers["RPP-Svtrid"] == "sv-chprov"
    body = response.json()
    assert body["@type"] == "domainTransferProcess" and body["transferDir"] == "pull"
    assert body["trStatus"] == "serverApproved"
    assert body["reqClientId"] == body["actClientId"] == "DENIC-1000022"
    assert "<domain:chprov>" in clients[0].sent[0]


def test_a_transfer_without_the_domain_data_is_a_bad_request():
    client, clients = setup()

    response = client.post(TRANSFER_URL, json={"@type": "domainTransferProcess"},
                           headers={**BODY_HEADERS, **AUTHORIZATION})

    assert response.status_code == 400, response.text
    assert all(not c.sent for c in clients)


def test_a_transfer_without_the_auth_info_sends_nothing():
    client, clients = setup()

    response = client.post(TRANSFER_URL, json=TRANSFER, headers=BODY_HEADERS)

    assert response.status_code == 400, response.text
    assert response.headers["RPP-Code"] == "02003"
    assert all(not c.sent for c in clients)


@pytest.mark.parametrize("method, url", [
    ("GET", f"{TRANSFER_URL}/latest"),
    ("DELETE", f"{TRANSFER_URL}/latest"),
    ("POST", f"{TRANSFER_URL}/latest/transferApprove"),
    ("POST", f"{TRANSFER_URL}/latest/transferReject"),
])
def test_transfer_operations_rri_lacks_answer_501(method, url):
    client, clients = setup()

    assert_refused(client.request(method, url, headers=HEADERS), clients, "02101")


def test_discovery_states_the_rri_extension():
    client, _ = setup()

    body = client.get("/.well-known/rpp", headers={"Accept": MEDIA_TYPE, "RPP-Cltrid": "cl-1"}).json()

    assert [(e["@type"], e["id"], e["name"]) for e in body["extensions"]] == [("extension", "rri", "DENIC RRI")]
    assert body["extensions"][0]["url"].startswith("https://")
