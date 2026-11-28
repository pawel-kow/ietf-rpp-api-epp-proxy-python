"""The verification information of a contact over the wire of the app composed for RRI (docs/rri/rri-extension.md):
`verifications` of create, read, full and partial update, and the refusals of the registry."""
import copy

import pytest

from tests.helper.fake_rri_client import error, reply
from tests.helper.presets import BASE
from tests.unit.test_preset_header_wire import named
from tests.unit.test_rri_adapter import CONTACT_INFO, REPLIES
from tests.unit.test_rri_wire import BODY_HEADERS, HEADERS, setup

HANDLE = "DENIC-1000022-HOLDER"

URL = f"/contacts/{HANDLE}"

BASE_HEADERS = {**named(BASE), "Content-Type": "application/rpp+json"}

BLOCK = {"@type": "verificationInformation", "claims": ["name"], "result": "success", "reference": "ABC123",
         "date": "2023-11-11T15:36:21+02:00", "evidence": "idcard", "method": "auth", "trustFramework": "de_denic"}

# What the INFO of the fixture states, as RPP shows it: claims in lower case, the date in UTC.
READ_BLOCK = {**BLOCK, "date": "2023-11-11T13:36:21.000000Z"}

CARD = {"@type": "Card", "version": "2.0", "kind": "individual", "name": {"full": "Erika Mustermann"},
        "addresses": {"addr": {"components": [{"kind": "name", "value": "Musterweg 12"},
                                              {"kind": "postcode", "value": "60596"},
                                              {"kind": "locality", "value": "Frankfurt am Main"}],
                               "countryCode": "DE"}},
        "phones": {"voice": {"number": "tel:+49.6912345678"}},
        "emails": {"email": {"address": "erika@example.com"}}}

CONTACT = {"@type": "contact", "contactInfo": CARD}

INFO_XML = (REPLIES / "contact_info.xml").read_text()

WITHOUT_BLOCK = INFO_XML[:INFO_XML.index("  <verification:verificationInformation")] + "</contact:infoData>\n"

NO_BLOCKS = reply(data=WITHOUT_BLOCK)

OTHER_EVIDENCE = reply(data=INFO_XML.replace("<verification:verificationEvidence>idcard<", "<verification:verificationEvidence>retina_scan<"))


def put(client, body, headers=BODY_HEADERS):
    return client.put(URL, json=body, headers=headers)


def test_the_read_shows_the_records_of_the_contact_in_utc_with_claims_in_lower_case():
    client, clients = setup(reply(data=INFO_XML.replace("<verification:claim>name<", "<verification:claim>Name<")))

    response = client.get(URL, headers=HEADERS)

    assert response.status_code == 200, response.text
    assert response.json()["verifications"] == [READ_BLOCK]
    assert clients[0].loggable == [False]       # the reply holds verification data


def test_the_base_preset_has_no_verifications_in_the_read():
    client, _ = setup(CONTACT_INFO)

    response = client.get(URL, headers=BASE_HEADERS)

    assert response.status_code == 200 and "verifications" not in response.json()


def test_a_contact_without_records_has_no_member():
    client, _ = setup(NO_BLOCKS)

    assert "verifications" not in client.get(URL, headers=HEADERS).json()


def test_create_sends_the_records_as_a_request_block_and_does_not_print_the_command():
    client, clients = setup(reply(), CONTACT_INFO)

    response = client.post("/contacts", json={**CONTACT, "id": HANDLE, "verifications": [BLOCK]}, headers=BODY_HEADERS)

    assert response.status_code == 201, response.text
    assert response.json()["verifications"] == [READ_BLOCK]
    sent = clients[0].sent[0]
    assert 'xsi:type="verification:verificationInformationType"' in sent
    assert "<verification:claim>name</verification:claim>" in sent and "ABC123" in sent
    assert "<verification:verificationTimestamp>2023-11-11T14:36:21+01:00<" in sent
    assert clients[0].loggable[0] is False


def test_create_without_records_sends_none_and_is_printed():
    client, clients = setup(reply(), NO_BLOCKS)

    response = client.post("/contacts", json={**CONTACT, "id": HANDLE}, headers=BODY_HEADERS)

    assert response.status_code == 201, response.text
    assert "verificationInformation" not in clients[0].sent[0] and clients[0].loggable[0] is True


def broken(change):
    return {**copy.deepcopy(BLOCK), **change}


@pytest.mark.parametrize("blocks", [
    [{key: value for key, value in BLOCK.items() if key != "evidence"}],
    [broken({"evidence": "retina_scan"})],
    [broken({"method": "telepathy"})],
    [broken({"trustFramework": "other"})],
    [broken({"claims": []})],
    [broken({"claims": ["name", "name"]})],
    [broken({"claims": ["phone"]})],
    [broken({"result": "maybe"})],
    [broken({"reference": ""})],
    [BLOCK, BLOCK],
    [broken({"reference": f"R{n}"}) for n in range(6)],
])
def test_records_that_break_the_definition_are_refused_and_send_nothing(blocks):
    client, clients = setup()

    response = client.post("/contacts", json={**CONTACT, "id": HANDLE, "verifications": blocks}, headers=BODY_HEADERS)

    assert response.status_code == 400, response.text
    assert all(not c.sent for c in clients)


def test_the_base_preset_cannot_send_verifications():
    client, clients = setup()

    response = client.post("/contacts", json={**CONTACT, "id": HANDLE, "verifications": [BLOCK]}, headers=BASE_HEADERS)

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02001", response.text
    assert all(not c.sent for c in clients)


@pytest.mark.parametrize("code, status, rpp_code", [
    ("63200041860", 400, "02005"), ("63200041861", 400, "02005"), ("63200041862", 400, "02005"),
    ("63200041864", 400, "02005"), ("63200041865", 400, "02005"), ("63200041866", 400, "02005"),
    ("63200041863", 422, "02306"), ("63200041867", 422, "02306"),
])
def test_the_refusals_of_the_registry(code, status, rpp_code):
    client, _ = setup(error(code, "verification refused", "VerificationEvidence: idcard"))

    response = client.post("/contacts", json={**CONTACT, "id": HANDLE, "verifications": [BLOCK]}, headers=BODY_HEADERS)

    assert response.status_code == status and response.headers["RPP-Code"] == rpp_code, response.text
    assert "idcard" not in response.text.replace('"idcard"', "")  # the registry's argument is not passed on


def test_a_full_update_without_verifications_removes_them_under_the_rri_preset():
    client, clients = setup(CONTACT_INFO, reply(), NO_BLOCKS)

    response = put(client, CONTACT)

    assert response.status_code == 200, response.text
    assert "verifications" not in response.json()
    assert "<contact:update>" in clients[0].sent[1] and "verificationInformation" not in clients[0].sent[1]


def test_a_full_update_without_verifications_keeps_them_under_the_base_preset():
    client, clients = setup(CONTACT_INFO, reply(), CONTACT_INFO)
    changed = {**CONTACT, "contactInfo": {**CARD, "emails": {"email": {"address": "new@example.com"}}}}

    response = put(client, changed, BASE_HEADERS)

    assert response.status_code == 200, response.text
    assert "new@example.com" in clients[0].sent[1] and "ABC123" in clients[0].sent[1]


def test_a_full_update_that_repeats_the_read_changes_nothing_and_sends_no_update():
    client, clients = setup(CONTACT_INFO)

    response = put(client, {**CONTACT, "verifications": [BLOCK]})

    assert response.status_code == 200, response.text
    assert len(clients[0].sent) == 1 and response.json()["verifications"] == [READ_BLOCK]


def test_a_full_update_that_changes_only_the_records_is_sent():
    client, clients = setup(CONTACT_INFO, reply(), CONTACT_INFO)

    response = put(client, {**CONTACT, "verifications": [broken({"reference": "NEW1", "result": "failed"})]})

    assert response.status_code == 200, response.text
    assert "NEW1" in clients[0].sent[1] and "ABC123" not in clients[0].sent[1]
    assert clients[0].loggable[1] is False


def test_a_full_update_with_an_empty_list_removes_the_records():
    client, clients = setup(CONTACT_INFO, reply(), NO_BLOCKS)

    assert put(client, {**CONTACT, "verifications": []}).status_code == 200
    assert "verificationInformation" not in clients[0].sent[1]


def test_a_partial_update_of_another_member_leaves_a_record_the_definition_does_not_list_as_it_is():
    client, clients = setup(OTHER_EVIDENCE, reply(), OTHER_EVIDENCE)

    response = client.patch(URL, json=[{"op": "replace", "path": "/contactInfo/emails/email/address",
                                        "value": "new@example.com"}], headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "new@example.com" in clients[0].sent[1] and "retina_scan" in clients[0].sent[1]


def test_a_partial_update_adds_a_record():
    client, clients = setup(CONTACT_INFO, reply(), CONTACT_INFO)
    second = broken({"claims": ["email"], "result": "failed", "reference": "ABC123/45GHU",
                     "evidence": "email_ver_transaction_log", "method": "data"})

    response = client.patch(URL, json=[{"op": "add", "path": "/verifications", "value": second}], headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    sent = clients[0].sent[1]
    assert "ABC123/45GHU" in sent and "ABC123<" in sent and sent.count("verifications</") == 0
    assert sent.count("verification:verificationInformation ") == 2


def test_a_partial_update_adds_a_record_the_definition_refuses():
    client, clients = setup(CONTACT_INFO)

    response = client.patch(URL, json=[{"op": "add", "path": "/verifications", "value": broken({"evidence": "x"})}],
                            headers=BODY_HEADERS)

    assert response.status_code == 400, response.text
    assert len(clients[0].sent) == 1


def test_a_partial_update_removes_the_records():
    client, clients = setup(CONTACT_INFO, reply(), NO_BLOCKS)

    response = client.patch(URL, json=[{"op": "remove", "path": "/verifications"}], headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "verificationInformation" not in clients[0].sent[1]


def test_a_partial_update_under_the_base_preset_cannot_name_verifications():
    client, clients = setup(CONTACT_INFO)

    response = client.patch(URL, json=[{"op": "remove", "path": "/verifications"}], headers=BASE_HEADERS)

    assert response.status_code == 400, response.text


def test_a_partial_update_adds_the_first_record_to_a_contact_without_any():
    client, clients = setup(NO_BLOCKS, reply(), CONTACT_INFO)

    response = client.patch(URL, json=[{"op": "add", "path": "/verifications", "value": BLOCK}], headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "ABC123" in clients[0].sent[1]


def test_a_partial_update_removes_a_record_by_a_match_and_refuses_one_that_is_not_there():
    client, clients = setup(CONTACT_INFO, reply(), NO_BLOCKS, CONTACT_INFO)

    removed = client.patch(URL, json=[{"op": "remove", "path": "/verifications", "match": {"reference": "ABC123"}}],
                           headers=BODY_HEADERS)
    missing = client.patch(URL, json=[{"op": "remove", "path": "/verifications", "match": {"reference": "NOPE"}}],
                           headers=BODY_HEADERS)

    assert removed.status_code == 200, removed.text
    assert "verificationInformation" not in clients[0].sent[1]
    assert missing.status_code == 422 and missing.headers["RPP-Code"] == "02308", missing.text
