"""The organisation read of RRI: regacc INFO of any RegAcc (docs/rri/rri-extension.md, "Mapping of regacc INFO")."""
import base64
import logging

import pytest

from core.model.contact.address import Address
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.commands.organisation.common import dotted
from registry_adapter.rri.gateways.rri_backend import RriBackend
from tests.helper.fake_rri_client import FakeRriClient, error, reply
from tests.helper.profiles import RRI_PARTS, RRI_PROFILE
from tests.unit.test_rri_wire import BODY_HEADERS, HEADERS, MEDIA_TYPE, assert_refused, setup
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from extensions.rri.core.model.registrar_request_templates import RegistrarRequestTemplates, RequestTemplate

HANDLE = "DENIC-1000022"


def info(handle=HANDLE, member="DENIC-1000020", phones=("+49 69 27 235 0",), faxes=("+49 69 27 235 235",),
         urls=("https://www.example.com/",), templates=True, email="info@example.com", changed="2026-11-12T01:20:20+01:00"):
    contacts = ""
    if templates:
        contacts = ('<regacc:contact role="generalrequest"><contact:type>REQUEST</contact:type>'
                    '<contact:uri-template>https://www.example.com/contact?domain={Alabel}</contact:uri-template>'
                    '<contact:changed>2026-11-10T10:00:00+01:00</contact:changed></regacc:contact>'
                    '<regacc:contact role="abusecontact"><contact:type>REQUEST</contact:type>'
                    '<contact:uri-template>mailto:abuse@example.com</contact:uri-template>'
                    '<contact:changed>2026-11-10T10:00:00+01:00</contact:changed></regacc:contact>')
    return reply(data=(
        '<regacc:infoData xmlns:regacc="http://registry.denic.de/regacc/5.0" xmlns:contact="http://registry.denic.de/contact/5.0">'
        f'<regacc:handle>{handle}</regacc:handle><regacc:name>Example Registrar GmbH</regacc:name>'
        '<regacc:postal><regacc:address>Example Street 1</regacc:address><regacc:address>Floor 2</regacc:address>'
        '<regacc:postalCode>60311</regacc:postalCode><regacc:city>Frankfurt am Main</regacc:city>'
        '<regacc:countryCode>DE</regacc:countryCode></regacc:postal>'
        + "".join(f"<regacc:phone>{p}</regacc:phone>" for p in phones)
        + "".join(f"<regacc:fax>{f}</regacc:fax>" for f in faxes)
        + f'<regacc:email>{email}</regacc:email>'
        + "".join(f"<regacc:url>{u}</regacc:url>" for u in urls)
        + f'<regacc:memberacc>{member}</regacc:memberacc>{contacts}<regacc:changed>{changed}</regacc:changed></regacc:infoData>'))


def backend(*replies):
    client = FakeRriClient(replies=list(replies))
    return RriBackend(client, RRI_PROFILE, extension_parts=RRI_PARTS), client


def test_the_organisation_is_read_with_regacc_info():
    gateway, client = backend(info())

    response = gateway.organisations.info(HANDLE, "cl-1")

    assert "<regacc:info>" in client.sent[0] and f"<regacc:handle>{HANDLE}</regacc:handle>" in client.sent[0]
    assert "<ctid>" not in client.sent[0]
    org = response.payload
    assert (org.id, org.sponsor_id, org.parent, org.status, org.roles) == (HANDLE, HANDLE, "DENIC-1000020", ["ok"], {"registrar": ["ok"]})
    assert org.up_date == "2026-11-12T00:20:20.000000Z"
    assert org.address == Address(street=["Example Street 1", "Floor 2"], city="Frankfurt am Main", postalCode="60311", country="DE")
    assert (org.phones, org.faxes, org.urls) == (["+49.69272350"], ["+49.6927235235"], ["https://www.example.com/"])
    assert org.extensions[EXTENSION_ID] == RegistrarRequestTemplates(
        general_request=RequestTemplate(uri_template="https://www.example.com/contact?domain={Alabel}", up_date="2026-11-10T09:00:00.000000Z"),
        abuse=RequestTemplate(uri_template="mailto:abuse@example.com", up_date="2026-11-10T09:00:00.000000Z"))


def test_a_member_account_equal_to_the_regacc_is_no_parent_whatever_its_case():
    gateway, _ = backend(info(handle="DENIC-1000022", member="denic-1000022"))

    assert gateway.organisations.info(HANDLE).payload.parent is None


def test_a_template_without_a_uri_template_is_left_out():
    xml = info().replace("<contact:uri-template>mailto:abuse@example.com</contact:uri-template>", "")
    gateway, _ = backend(xml)

    templates = gateway.organisations.info(HANDLE).payload.extensions[EXTENSION_ID]

    assert templates.abuse is None and templates.general_request is not None


@pytest.mark.parametrize("number, expected", [
    ("+49 69 27 235 0", "+49.69272350"),
    ("+49 69 27235 290", "+49.6927235290"),
    ("+1-703-555-5555 x12", "+1.7035555555x12"),
    ("+1.7035555555", "+1.7035555555"),
    ("+49/89/323560", "+49.89323560"),
    ("+4969272350", None),
    ("+49", None),
    ("+1234 5", None),
    ("+49 1234567890123456", None),
    ("+49 69x", None),
])
def test_an_e123_number_becomes_the_dotted_one_or_is_left_out(number, expected):
    assert dotted(number) == expected


def test_what_gives_no_value_is_left_out_and_logged_by_name(caplog):
    gateway, _ = backend(info(phones=("+4969272350", "+49 69 1"), faxes=("0049 69 1",), urls=("www.example.com", "ftp://x.example/")))

    with caplog.at_level(logging.WARNING):
        org = gateway.organisations.info(HANDLE).payload

    assert (org.phones, org.faxes, org.urls) == (["+49.691"], [], ["ftp://x.example/"])
    assert "4969272350" not in caplog.text and "www.example.com" not in caplog.text
    assert "a phone" in caplog.text and "a fax" in caplog.text and "a url" in caplog.text


def test_the_refusals_of_regacc_info():
    gateway, _ = backend(error("63300062010", "RegAcc does not exist"), error("63310062008", "Invalid value"),
                         error("83000000004", "XSD"))

    codes = [gateway.organisations.info(h) for h in ("DENIC-9", "DENIC-999999999999", "NOPE")]

    assert all(isinstance(c, ErrorResponse) for c in codes)
    assert [c.code for c in codes] == [ResultCode.OBJECT_DOES_NOT_EXIST] + [ResultCode.PARAMETER_VALUE_SYNTAX_ERROR] * 2


# --- the wire

def test_the_organisation_is_read_with_the_templates_of_the_rri_extension():
    client, clients = setup(info())

    response = client.get(f"/organisations/{HANDLE}", headers=HEADERS)

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == HANDLE and body["provMetadata"] == {
        "@type": "provMetadata", "spClientId": HANDLE, "upDate": "2026-11-12T00:20:20.000000Z"}
    assert body["status"] == [{"@type": "organisationStatus", "label": "ok"}]
    assert body["roles"] == {"registrar": {"@type": "organisationRole", "status": [{"@type": "organisationRoleStatus", "label": "ok"}]}}
    assert body["parent"] == {"@type": "organisation", "id": "DENIC-1000020"}
    card = body["contactInfo"]
    assert card["kind"] == "org" and card["name"] == {"full": "Example Registrar GmbH"}
    assert card["phones"] == {"voice": {"number": "tel:+49.69272350"}, "fax": {"number": "tel:+49.6927235235", "features": {"fax": True}}}
    assert card["links"] == {"url": {"uri": "https://www.example.com/"}}
    assert card["emails"] == {"email": {"address": "info@example.com"}}
    assert [c["value"] for c in card["addresses"]["addr"]["components"]] == ["Example Street 1", "Floor 2", "Frankfurt am Main", "60311"]
    assert body["generalRequestTemplate"]["uriTemplate"] == "https://www.example.com/contact?domain={Alabel}"
    assert body["abuseTemplate"] == {"@type": "requestTemplate", "uriTemplate": "mailto:abuse@example.com",
                                     "upDate": "2026-11-10T09:00:00.000000Z"}
    assert response.headers["RPP-Cltrid"] == "cl-1"


def test_a_preset_without_the_extension_shows_no_templates():
    client, _ = setup(info())

    response = client.get(f"/organisations/{HANDLE}", headers={**HEADERS, "RPP-Preset": "preset=urn:ietf:params:rpp:preset:base;version=1.0"})

    assert response.status_code == 200, response.text
    assert "generalRequestTemplate" not in response.json() and "abuseTemplate" not in response.json()


def test_several_numbers_take_the_numbered_keys_and_only_the_first_url_is_shown():
    client, _ = setup(info(phones=("+49 69 1", "+49 69 2"), faxes=("+49 69 3", "+49 69 4"), urls=("https://a.example/", "https://b.example/")))

    response = client.get(f"/organisations/{HANDLE}", headers=HEADERS)
    assert response.status_code == 200, response.text
    card = response.json()["contactInfo"]

    assert sorted(card["phones"]) == ["fax", "fax-1", "voice", "voice-1"]
    assert list(card["links"]) == ["url"]      # RecordLink has no url-1: the further URL is left out


def test_an_entry_that_fails_its_definition_is_left_out_not_a_500(caplog):
    client, _ = setup(info(email="not an email"))

    with caplog.at_level(logging.WARNING):
        response = client.get(f"/organisations/{HANDLE}", headers=HEADERS)

    assert response.status_code == 200, response.text
    card = response.json()["contactInfo"]
    assert "emails" not in card and "links" in card
    assert "emails" in caplog.text and "not an email" not in caplog.text


def test_includeElements_names_a_data_element_of_the_organisation():
    client, _ = setup(info())

    assert client.get(f"/organisations/{HANDLE}?includeElements=nope", headers=HEADERS).status_code == 400
    assert client.get(f"/organisations/{HANDLE}?includeElements=contactInfo", headers=HEADERS).status_code == 200


@pytest.mark.parametrize("code, status, rpp_code", [
    ("63300062010", 404, "02303"), ("63310062008", 400, "02005"), ("83000000004", 400, "02005")])
def test_the_refusals_of_the_registry(code, status, rpp_code):
    client, _ = setup(error(code, "refused"))

    response = client.get(f"/organisations/{HANDLE}", headers=HEADERS)

    assert (response.status_code, response.headers["RPP-Code"]) == (status, rpp_code)


@pytest.mark.parametrize("method, url, body", [
    ("POST", "/organisations", {"@type": "organisation"}),
    ("PUT", f"/organisations/{HANDLE}", {"@type": "organisation"}),
    ("PATCH", f"/organisations/{HANDLE}", []),
    ("DELETE", f"/organisations/{HANDLE}", None),
    ("GET", f"/organisations/{HANDLE}/processes", None),
])
def test_what_the_registry_maintains_outside_rri_is_501(method, url, body):
    client, clients = setup()

    response = client.request(method, url, json=body, headers=BODY_HEADERS if body is not None else HEADERS)

    assert_refused(response, clients, "02101")
