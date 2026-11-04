import pytest

from models import Address, AuthInfo, Contact, ContactType
from rpp_to_model_mapper import UnsupportedRppFeature, contact_to_rpp, rpp_to_contact


def card(**extra):
    return {"@type": "Card", "version": "2.0", "kind": "individual", "name": {"full": "John Doe"}, **extra}


def create_body(contact_info=None, **extra):
    return {"@type": "contact", "id": "JD-1234", "contactInfo": contact_info or card(), **extra}


def address(*components, **extra):
    return {"addr": {"components": [{"kind": k, "value": v} for k, v in components], **extra}}


def info_contact(**extra):
    fields = {"id": "JD-1234", "type": ContactType.PERSON, "name": "John Doe", "status": ["ok"], "clID": "ClientX"}
    return Contact(**{**fields, **extra})


def test_create_maps_identity():
    contact = rpp_to_contact(create_body())

    assert (contact.id, contact.name, contact.type) == ("JD-1234", "John Doe", ContactType.PERSON)


def test_create_without_kind_is_an_individual():
    body = create_body({"@type": "Card", "version": "2.0", "name": {"full": "John Doe"}})

    assert rpp_to_contact(body).type == ContactType.PERSON


def test_create_maps_org_card():
    body = create_body(card(kind="org", organizations={"org": {"name": "Example Inc."}}))

    contact = rpp_to_contact(body)
    assert (contact.type, contact.organisationName) == (ContactType.ORG, "Example Inc.")


def test_create_maps_address_components():
    body = create_body(card(addresses=address(
        ("name", "Line 1"), ("name", "Line 2"), ("locality", "Dulles"),
        ("region", "VA"), ("postcode", "20166"), countryCode="US",
    )))

    assert rpp_to_contact(body).address == Address(
        street=["Line 1", "Line 2"], city="Dulles", stateProvince="VA", postalCode="20166", country="US",
    )


def test_create_maps_email():
    body = create_body(card(emails={"email": {"address": "jdoe@example.example"}}))

    assert rpp_to_contact(body).email == ["jdoe@example.example"]


@pytest.mark.parametrize("tel, e164", [
    ("tel:+1-703-555-5555", "+1.7035555555"),
    ("tel:+49-123123123;ext=123", "+49.123123123x123"),
])
def test_create_maps_tel_uri_to_epp_number(tel, e164):
    body = create_body(card(phones={"voice": {"number": tel}}))

    assert rpp_to_contact(body).phone == [e164]


@pytest.mark.parametrize("number", ["+1.7035555555", "tel:+17035555555", "703-555-5555"])
def test_create_rejects_numbers_without_a_tel_country_code_separator(number):
    body = create_body(card(phones={"voice": {"number": number}}))

    with pytest.raises(ValueError):
        rpp_to_contact(body)


def test_create_splits_voice_and_fax_by_features():
    body = create_body(card(phones={
        "a": {"number": "tel:+1-703-555-5555"},
        "b": {"number": "tel:+1-703-555-5556", "features": {"fax": True}},
    }))

    contact = rpp_to_contact(body)
    assert (contact.phone, contact.fax) == (["+1.7035555555"], ["+1.7035555556"])


def test_create_maps_authinfo():
    body = create_body(authInfo={"@type": "authInfo", "method": "authinfo", "authdata": "2fooBAR"})

    assert rpp_to_contact(body).authInfo == AuthInfo(pw="2fooBAR")


VOICE = {"number": "tel:+1-703-555-5555"}
EMAIL = {"address": "a@example.example"}


@pytest.mark.parametrize("body", [
    create_body(card(organizations={"org": {"name": "Example Inc."}})),
    create_body(card(language="en")),
    create_body(card(links={"l": {"uri": "https://example.example"}})),
    create_body(card(localizations={"de": {}})),
    create_body(card(name={"components": [{"kind": "given", "value": "John"}]})),
    create_body(card(addresses=address(full="1 Example Dr"))),
    create_body(card(addresses=address(("country", "USA")))),
    create_body(card(addresses={**address(("locality", "A"), countryCode="US"), "b": {"countryCode": "US"}})),
    create_body(card(kind="org", organizations={"a": {"name": "A"}, "b": {"name": "B"}})),
    create_body(card(emails={"a": EMAIL, "b": EMAIL})),
    create_body(card(phones={"a": VOICE, "b": VOICE})),
    create_body(card(phones={"a": {**VOICE, "features": {"text": True}}})),
    create_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited"}]),
    create_body(disclose={"@type": "disclose"}),
    create_body(authInfo={"@type": "authInfo", "method": "other", "authdata": "x"}),
])
def test_create_rejects_what_the_model_cannot_hold(body):
    with pytest.raises(UnsupportedRppFeature):
        rpp_to_contact(body)


def test_read_builds_the_card():
    rpp = contact_to_rpp(info_contact(
        email=["jdoe@example.example"],
        phone=["+1.7035555555x12"],
        fax=["+1.7035555556"],
        address=Address(street=["Line 1"], city="Dulles", stateProvince="VA", postalCode="20166", country="US"),
    ))

    assert rpp["contactInfo"] == {
        "@type": "Card",
        "version": "2.0",
        "kind": "individual",
        "name": {"full": "John Doe"},
        "addresses": {"addr": {
            "components": [
                {"kind": "name", "value": "Line 1"},
                {"kind": "locality", "value": "Dulles"},
                {"kind": "region", "value": "VA"},
                {"kind": "postcode", "value": "20166"},
            ],
            "countryCode": "US",
        }},
        "phones": {
            "voice": {"number": "tel:+1-7035555555;ext=12"},
            "fax": {"number": "tel:+1-7035555556", "features": {"fax": True}},
        },
        "emails": {"email": {"address": "jdoe@example.example"}},
    }


def test_read_maps_org_kind():
    rpp = contact_to_rpp(info_contact(type=ContactType.ORG, organisationName="Example Inc."))

    assert rpp["contactInfo"]["kind"] == "org"
    assert rpp["contactInfo"]["organizations"] == {"org": {"name": "Example Inc."}}


def test_read_leaves_out_kind_when_undefined():
    assert "kind" not in contact_to_rpp(info_contact(type=ContactType.UNDEFINED))["contactInfo"]


def test_read_maps_metadata_and_status():
    rpp = contact_to_rpp(info_contact(crID="ClientY"))

    assert rpp["@type"] == "contact"
    assert rpp["provMetadata"] == {"@type": "provMetadata", "spClientId": "ClientX", "crClientId": "ClientY"}
    assert rpp["status"] == [{"@type": "contactStatus", "label": "ok"}]
