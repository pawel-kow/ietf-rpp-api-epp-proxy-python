"""The Verification Process Object over the wire of the app composed for RRI (docs/rri/rri-extension.md): a recursive domain
INFO, for the sponsor in full and for another client with Object Authorisation reduced."""
import base64

import pytest

from rpp.mapping.shared.rpp_authorization import MALFORMED
from tests.helper.fake_rri_client import error, reply
from tests.helper.presets import BASE
from tests.unit.test_preset_header_wire import named
from tests.unit.test_rri_adapter import DOMAIN_INFO, NAME
from tests.unit.test_rri_wire import HEADERS, setup

URL = f"/domainNames/{NAME}/processes/verificationProcesses/latest"

SECRET = "Abc23456"

AUTHORIZATION = {**HEADERS, "RPP-Authorization": "authinfo value=" + base64.b64encode(SECRET.encode()).decode()}

NAMESPACES = ('xmlns:domain="http://registry.denic.de/domain/5.0" xmlns:contact="http://registry.denic.de/contact/5.0" '
              'xmlns:verification="http://registry.denic.de/verification/5.0" '
              'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"')

FULL = ('<verification:verificationInformation xsi:type="verification:domainVerificationInformationType">'
        '<verification:verifiedClaims><verification:claim>name</verification:claim></verification:verifiedClaims>'
        '<verification:verificationResult>failed</verification:verificationResult>'
        '<verification:verificationReference>REF-SECRET-1</verification:verificationReference>'
        '<verification:verificationTimestamp>2026-11-12T10:00:00+01:00</verification:verificationTimestamp>'
        '<verification:verificationEvidence>idcard</verification:verificationEvidence>'
        '<verification:verificationMethod>auth</verification:verificationMethod>'
        '<verification:trustFramework>de_denic</verification:trustFramework>'
        '</verification:verificationInformation>')

REDUCED = ('<verification:verificationInformation xsi:type="verification:domainVerificationInformationType">'
           '<verification:verifiedClaims><verification:claim>name</verification:claim></verification:verifiedClaims>'
           '<verification:verificationResult>failed</verification:verificationResult>'
           '</verification:verificationInformation>')

DEADLINES = ('<domain:verificationDeadlineBeforeDedelegation>2026-11-20T00:00:00+01:00</domain:verificationDeadlineBeforeDedelegation>'
             '<domain:verificationDeadlineBeforeDeletion>2027-02-18T00:00:00+01:00</domain:verificationDeadlineBeforeDeletion>')


def info(holders, deadlines=DEADLINES, sponsor="DENIC-1000022"):
    data = (f'<domain:infoData {NAMESPACES}><domain:handle>{NAME}</domain:handle><domain:ace>{NAME}</domain:ace>'
            f'<domain:status>serverHold</domain:status>{holders}{deadlines}<domain:changed>2026-11-12T01:20:33+01:00</domain:changed>'
            f'<domain:regAcc><domain:regAccId>{sponsor}</domain:regAccId><domain:name>Example</domain:name></domain:regAcc>'
            '</domain:infoData>')
    return reply(data=data)


def holder(handle, blocks):
    handle_xml = f"<contact:handle>{handle}</contact:handle>" if handle else ""
    return f'<domain:contact role="holder">{handle_xml}{blocks}</domain:contact>'


OWN = info(holder("DENIC-1000022-A", FULL) + holder("DENIC-1000022-B", ""))

FOREIGN = info(holder(None, REDUCED) + holder(None, ""), sponsor="DENIC-1000099")


def test_the_sponsor_reads_the_deadlines_and_the_holders_in_full():
    client, clients = setup(OWN)

    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 200, response.text
    assert "Location" not in response.headers
    assert response.json() == {
        "@type": "verificationProcess",
        "holdDeadline": "2026-11-19T23:00:00.000000Z", "deletionDeadline": "2027-02-17T23:00:00.000000Z",
        "holders": [
            {"@type": "holderVerification", "holder": {"@type": "contact", "id": "DENIC-1000022-A"},
             "verifications": [{"@type": "verificationInformation", "claims": ["name"], "result": "failed",
                                "reference": "REF-SECRET-1", "date": "2026-11-12T09:00:00.000000Z",
                                "evidence": "idcard", "method": "auth", "trustFramework": "de_denic"}]},
            {"@type": "holderVerification", "holder": {"@type": "contact", "id": "DENIC-1000022-B"}},
        ]}
    sent = clients[0].sent[0]
    assert '<domain:info recursive="true">' in sent or 'recursive="true"' in sent
    assert "<domain:authInfo>" not in sent
    assert clients[0].loggable == [False]


def test_another_client_with_object_authorisation_reads_it_reduced_and_sends_the_value_as_authinfo():
    client, clients = setup(FOREIGN)

    response = client.get(URL, headers=AUTHORIZATION)

    assert response.status_code == 200, response.text
    assert response.json() == {
        "@type": "verificationProcess",
        "holdDeadline": "2026-11-19T23:00:00.000000Z", "deletionDeadline": "2027-02-17T23:00:00.000000Z",
        "holders": [{"@type": "holderVerification",
                     "verifications": [{"@type": "verificationInformation", "claims": ["name"], "result": "failed"}]},
                    {"@type": "holderVerification"}]}
    assert f"<domain:authInfo>{SECRET}</domain:authInfo>" in clients[0].sent[0]
    assert clients[0].loggable == [False]


def test_another_client_gets_no_more_than_the_claims_and_the_result_whatever_the_registry_returns():
    client, _ = setup(info(holder("DENIC-1000099-A", FULL), sponsor="DENIC-1000099"))

    response = client.get(URL, headers=AUTHORIZATION)

    assert response.status_code == 200, response.text
    assert "REF-SECRET-1" not in response.text and "DENIC-1000099-A" not in response.text
    assert response.json()["holders"] == [{"@type": "holderVerification", "verifications": [
        {"@type": "verificationInformation", "claims": ["name"], "result": "failed"}]}]


def test_another_client_without_object_authorisation_is_refused():
    client, _ = setup(FOREIGN)

    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 403 and response.headers["RPP-Code"] == "02201", response.text


def test_a_wrong_authorisation_is_the_registrys_refusal():
    client, _ = setup(error("63370088701", "AuthInfo does not match"))

    response = client.get(URL, headers=AUTHORIZATION)

    assert response.status_code == 401 and response.headers["RPP-Code"] == "02202", response.text
    assert SECRET not in response.text


def test_a_domain_without_a_deadline_has_no_process():
    client, _ = setup(info(holder("DENIC-1000022-A", ""), deadlines=""))

    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 404 and response.headers["RPP-Code"] == "02303", response.text


def test_a_deadline_without_a_holder_is_no_process_either():
    client, _ = setup(info(""))

    assert client.get(URL, headers=HEADERS).status_code == 404


def test_one_deadline_is_enough():
    deadline = ('<domain:verificationDeadlineBeforeDeletion>2027-02-18T00:00:00+01:00'
                '</domain:verificationDeadlineBeforeDeletion>')
    client, _ = setup(info(holder("DENIC-1000022-A", ""), deadlines=deadline))

    body = client.get(URL, headers=HEADERS).json()

    assert "holdDeadline" not in body and body["deletionDeadline"] == "2027-02-17T23:00:00.000000Z"


def test_a_domain_that_does_not_exist_is_404():
    client, _ = setup(error("63300062009", "Domain does not exist"))

    assert client.get(URL, headers=HEADERS).status_code == 404


def test_a_malformed_authorisation_sends_nothing():
    client, clients = setup()

    response = client.get(URL, headers={**HEADERS, "RPP-Authorization": "authinfo value=%%%"})

    assert response.status_code == 400 and all(not c.sent for c in clients)


@pytest.mark.parametrize("method, path", [
    ("POST", f"/domainNames/{NAME}/processes/verificationProcesses"),
    ("GET", f"/domainNames/{NAME}/processes/verificationProcesses"),
    ("GET", f"/domainNames/{NAME}/processes/verificationProcesses/p1"),
    ("DELETE", f"/domainNames/{NAME}/processes/verificationProcesses/p1"),
    ("DELETE", f"/domainNames/{NAME}/processes/verificationProcesses/latest"),
])
def test_the_other_operations_are_not_implemented_and_send_nothing(method, path):
    client, clients = setup()

    response = client.request(method, path, json={"@type": "verificationProcess"},
                              headers={**HEADERS, "Content-Type": "application/rpp+json"})

    assert response.status_code == 501 and response.headers["RPP-Code"] == "02101", response.text
    assert all(not c.sent for c in clients)


def test_the_base_preset_has_no_verification_process():
    client, clients = setup()

    response = client.get(URL, headers=named(BASE))

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02001", response.text
    assert all(not c.sent for c in clients)
