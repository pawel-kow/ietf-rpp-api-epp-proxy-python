"""The Process Objects of authorisation information over the wire of the app composed for RRI
(docs/rri/rri-extension.md): `authInfoProcess` (AuthInfo1, CREATE-AUTHINFO1, INFO, DELETE-AUTHINFO1) and
`authInfoIssueProcess` (AuthInfo2, CREATE-AUTHINFO2)."""
import hashlib
import re

import pytest

from tests.helper.fake_rri_client import error, reply
from tests.unit.test_presets_wire import BASE, rri_client
from tests.unit.test_rri_adapter import DOMAIN_INFO, NAME
from tests.unit.test_rri_wire import BODY_HEADERS, HEADERS, setup

URL = f"/domainNames/{NAME}/processes/authInfoProcesses"

LATEST = f"{URL}/latest"

ISSUE = f"/domainNames/{NAME}/processes/authInfoIssueProcesses"

SECRET = "Abc23456"

CREATE = {"@type": "authInfoProcess", "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": SECRET}}

# The domain INFO of the fixture states authInfo1 as 2026-11-14T00:00:00+01:00: the instant it expires, in the registry's
# offset, so the last day it is valid is the day before (not a day of UTC either).
STATED = "2026-11-13"

WITHOUT = DOMAIN_INFO.replace("<domain:authInfo1>2026-11-14T00:00:00+01:00</domain:authInfo1>", "")

FOREIGN = DOMAIN_INFO.replace("DENIC-1000022</domain:regAccId>", "DENIC-1000099</domain:regAccId>")


def test_create_sends_the_hash_and_the_expiry_date_and_reads_the_date_back():
    client, clients = setup(reply(), DOMAIN_INFO)

    response = client.post(URL, json={**CREATE, "expiryDate": "2026-11-13"}, headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "Location" not in response.headers
    assert response.json() == {"@type": "authInfoProcess", "expiryDate": STATED}
    sent = clients[0].sent[0]
    assert f'hash="{hashlib.sha256(SECRET.encode()).hexdigest()}"' in sent and 'expire="20261113"' in sent
    assert "<domain:info" in clients[0].sent[1]


def test_create_without_an_expiry_date_leaves_it_to_the_registry():
    client, clients = setup(reply(), DOMAIN_INFO)

    response = client.post(URL, json=CREATE, headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "expire=" not in clients[0].sent[0]
    assert response.json()["expiryDate"] == STATED


def test_create_does_not_print_the_hash_or_return_the_secret():
    client, clients = setup(reply(), DOMAIN_INFO)

    response = client.post(URL, json=CREATE, headers=BODY_HEADERS)

    assert clients[0].loggable[0] is False
    assert SECRET not in response.text and "authInfo" not in response.json()


def test_create_whose_read_back_fails_answers_the_date_asked_for():
    client, _ = setup(reply(), error("53000000012", "busy"))

    response = client.post(URL, json={**CREATE, "expiryDate": "2026-12-01"}, headers=BODY_HEADERS)

    assert response.status_code == 200 and response.json() == {"@type": "authInfoProcess", "expiryDate": "2026-12-01"}


def test_create_whose_read_back_fails_without_a_date_answers_the_bare_process():
    client, _ = setup(reply(), error("53000000012", "busy"))

    response = client.post(URL, json=CREATE, headers=BODY_HEADERS)

    assert response.status_code == 200 and response.json() == {"@type": "authInfoProcess"}


def test_an_existing_authinfo1_is_a_conflict():
    client, _ = setup(error("63391068704", "AuthInfo1 already exists"))

    response = client.post(URL, json=CREATE, headers=BODY_HEADERS)

    assert response.status_code == 409 and response.headers["RPP-Code"] == "02302"


@pytest.mark.parametrize("code", ["63391068618", "63391068603"])
def test_an_expiry_date_the_registry_refuses_is_a_range_error(code):
    client, _ = setup(error(code, "expire refused"))

    response = client.post(URL, json={**CREATE, "expiryDate": "2026-12-12"}, headers=BODY_HEADERS)

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02004"


def test_another_method_than_authinfo_is_unsupported_and_sends_nothing():
    client, clients = setup()
    body = {**CREATE, "authInfo": {"@type": "authInfo", "method": "other", "authdata": SECRET}}

    response = client.post(URL, json=body, headers=BODY_HEADERS)

    assert response.status_code == 501 and response.headers["RPP-Code"] == "02102"
    assert all(not c.sent for c in clients)


def test_a_secret_outside_the_registrys_set_is_refused_and_sends_nothing():
    client, clients = setup()
    body = {**CREATE, "authInfo": {"@type": "authInfo", "method": "authinfo", "authdata": "Password1!@"}}

    response = client.post(URL, json=body, headers=BODY_HEADERS)

    assert response.status_code == 422 and response.headers["RPP-Code"] == "02306"
    assert all(not c.sent for c in clients)
    assert "Password1" not in response.text


@pytest.mark.parametrize("body", [{"@type": "authInfoProcess"}, {**CREATE, "expiryDate": "tomorrow"},
                                  {**CREATE, "other": 1}])
def test_an_invalid_create_is_a_bad_request(body):
    client, clients = setup()

    response = client.post(URL, json=body, headers=BODY_HEADERS)

    assert response.status_code == 400, response.text
    assert all(not c.sent for c in clients)


def test_another_client_is_refused_by_the_registry():
    client, _ = setup(error("63300022003", "domain of another provider"))

    response = client.post(URL, json=CREATE, headers=BODY_HEADERS)

    assert response.status_code == 403 and response.headers["RPP-Code"] == "02201"


def test_read_answers_the_date_the_registry_states():
    client, clients = setup(DOMAIN_INFO)

    response = client.get(LATEST, headers=HEADERS)

    assert response.status_code == 200, response.text
    assert response.json() == {"@type": "authInfoProcess", "expiryDate": STATED}


def test_read_of_an_authinfo1_that_expires_during_a_day_answers_that_day():
    client, _ = setup(DOMAIN_INFO.replace("2026-11-14T00:00:00+01:00", "2026-11-14T13:30:00+01:00"))

    response = client.get(LATEST, headers=HEADERS)

    assert response.json()["expiryDate"] == "2026-11-14"


def test_read_of_a_domain_without_authinfo1_is_not_found():
    client, _ = setup(WITHOUT)

    response = client.get(LATEST, headers=HEADERS)

    assert response.status_code == 404 and response.headers["RPP-Code"] == "02303"


def test_read_of_a_domain_of_another_client_is_forbidden():
    client, _ = setup(FOREIGN)

    response = client.get(LATEST, headers=HEADERS)

    assert response.status_code == 403 and response.headers["RPP-Code"] == "02201"
    assert STATED not in response.text


def test_delete_sends_delete_authinfo1():
    client, clients = setup(reply())

    response = client.delete(LATEST, headers=HEADERS)

    assert response.status_code == 200, response.text
    assert "<domain:deleteAuthInfo1" in clients[0].sent[0]


def test_delete_without_authinfo1_is_not_found():
    client, _ = setup(error("63392068709", "AuthInfo1 does not exist"))

    response = client.delete(LATEST, headers=HEADERS)

    assert response.status_code == 404 and response.headers["RPP-Code"] == "02303"


def test_delete_of_a_domain_of_another_client_is_forbidden():
    client, _ = setup(error("63300022003", "domain of another provider"))

    response = client.delete(LATEST, headers=HEADERS)

    assert response.status_code == 403 and response.headers["RPP-Code"] == "02201"


def test_issue_sends_create_authinfo2_and_returns_nothing_of_it():
    client, clients = setup(reply())

    response = client.post(ISSUE, json={"@type": "authInfoIssueProcess"}, headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "Location" not in response.headers
    assert response.json() == {"@type": "authInfoIssueProcess"}
    assert re.search(r"<domain:createAuthInfo2[ >]", clients[0].sent[0])


def test_issue_with_an_existing_authinfo2_is_a_conflict():
    client, _ = setup(error("63393068704", "AuthInfo2 already exists"))

    response = client.post(ISSUE, json={"@type": "authInfoIssueProcess"}, headers=BODY_HEADERS)

    assert response.status_code == 409 and response.headers["RPP-Code"] == "02302"


def test_issue_of_a_domain_that_does_not_exist_is_not_found():
    client, _ = setup(error("63300062009", "domain does not exist"))

    response = client.post(ISSUE, json={"@type": "authInfoIssueProcess"}, headers=BODY_HEADERS)

    assert response.status_code == 404 and response.headers["RPP-Code"] == "02303"


@pytest.mark.parametrize("method, url, body", [
    ("GET", ISSUE, None),
    ("GET", f"{ISSUE}/latest", None),
    ("DELETE", f"{ISSUE}/latest", None),
    ("GET", URL, None),
    ("GET", f"{URL}/p1", None),
    ("DELETE", f"{URL}/p1", None),
])
def test_the_operations_the_extension_does_not_define_are_not_implemented(method, url, body):
    client, clients = setup()

    response = client.request(method, url, headers=HEADERS)

    assert response.status_code == 501 and response.headers["RPP-Code"] == "02101"
    assert all(not c.sent for c in clients)


@pytest.mark.parametrize("method, url, body", [
    ("POST", URL, CREATE),
    ("GET", LATEST, None),
    ("DELETE", LATEST, None),
    ("POST", ISSUE, {"@type": "authInfoIssueProcess"}),
])
def test_a_preset_without_the_extension_refuses_the_process_paths(method, url, body):
    client = rri_client()
    headers = {**BODY_HEADERS, "RPP-Preset": f"preset={BASE};version=1.0"}

    response = client.request(method, url, json=body, headers=headers)

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02001", response.text


def test_the_processes_of_the_base_are_not_affected_by_the_preset_check():
    client, clients = setup()
    headers = {**BODY_HEADERS, "RPP-Preset": f"preset={BASE};version=1.0"}

    response = client.post(f"/domainNames/{NAME}/processes/renewProcesses", json={"@type": "renewProcess"},
                           headers=headers)

    assert response.status_code != 400 or response.headers["RPP-Code"] != "02001"


def test_read_of_an_authinfo1_the_proxy_cannot_read_answers_the_process_without_a_date():
    client, _ = setup(DOMAIN_INFO.replace("2026-11-14T00:00:00+01:00", "nonsense"))

    response = client.get(LATEST, headers=HEADERS)

    assert response.status_code == 200 and response.json() == {"@type": "authInfoProcess"}
