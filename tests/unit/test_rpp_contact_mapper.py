import copy

import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from tests.helper.epp_app_context import epp_app_context  # noqa: F401, a fixture
from models import Address, AuthInfo, Contact, ContactType, LocalizedPostalInfo
from rpp_schema_validator import validate_schema
from rpp_to_model_mapper import contacts

pytestmark = pytest.mark.usefixtures("epp_app_context")


def card(**extra):
    return {"@type": "Card", "version": "2.0", "kind": "individual", "name": {"full": "John Doe"}, **extra}


def org_card(**extra):
    return card(**{"kind": "org", "organizations": {"org": {"name": "Example Inc."}}, **extra})


def create_body(contact_info=None, **extra):
    return {"@type": "contact", "id": "JD-1234", "contactInfo": contact_info or card(), **extra}


def components(*entries):
    return [{"kind": k, "value": v} for k, v in entries]


def postal(*entries, **extra):
    """One Address: locality and country unless the test gives its own."""
    return {"components": components(*(entries or [("locality", "Dulles")])), "countryCode": "US", **extra}


def address(*entries, **extra):
    return {"addr": postal(*entries, **extra)}


def info_contact(**extra):
    fields = {"id": "JD-1234", "type": ContactType.PERSON, "name": "John Doe", "status": ["ok"], "clID": "ClientX"}
    return Contact(**{**fields, **extra})


def rejected_status(body):
    with pytest.raises(ProblemException) as rejected:
        map_request(contacts.rpp_to_model, body)
    return rejected.value.status


def test_create_maps_identity():
    contact = contacts.rpp_to_model(create_body())

    assert (contact.id, contact.name, contact.type) == ("JD-1234", "John Doe", ContactType.PERSON)


def test_create_without_kind_is_an_individual():
    body = create_body({"@type": "Card", "version": "2.0", "name": {"full": "John Doe"}})

    assert contacts.rpp_to_model(body).type == ContactType.PERSON


def test_create_maps_org_card():
    contact = contacts.rpp_to_model(create_body(org_card()))

    assert (contact.type, contact.organisationName) == (ContactType.ORG, "Example Inc.")


def test_create_maps_address_components():
    body = create_body(card(addresses=address(
        ("name", "Line 1"), ("name", "Line 2"), ("locality", "Dulles"),
        ("region", "VA"), ("postcode", "20166"),
    )))

    assert contacts.rpp_to_model(body).address == Address(
        street=["Line 1", "Line 2"], city="Dulles", stateProvince="VA", postalCode="20166", country="US",
    )


def test_create_keeps_the_order_of_street_lines():
    body = create_body(card(addresses=address(
        ("name", "B"), ("locality", "Dulles"), ("name", "A"), ("name", "C"),
    )))

    assert contacts.rpp_to_model(body).address.street == ["B", "A", "C"]


def test_create_maps_email():
    body = create_body(card(emails={"email": {"address": "jdoe@example.example"}}))

    assert contacts.rpp_to_model(body).email == ["jdoe@example.example"]


@pytest.mark.parametrize("tel, e164", [
    ("tel:+49.6215550100", "+49.6215550100"),
    ("tel:+49.6215550100;ext=123", "+49.6215550100x123"),
    ("tel:+1.2", "+1.2"),
    ("tel:+123.123456789012", "+123.123456789012"),
])
def test_create_maps_tel_uri_to_epp_number(tel, e164):
    body = create_body(card(phones={"voice": {"number": tel}}))

    assert contacts.rpp_to_model(body).phone == [e164]


@pytest.mark.parametrize("number", [
    "+1.7035555555",
    "tel:+17035555555",
    "703-555-5555",
    "tel:+1-703-555-5555",
    "tel:+1.703-555-5555",
    "tel:7035555555",
    "tel:+1234.5555555",
    "tel:+1.123456789012345",
    "tel:+123.1234567890123",
    "tel:+1.7035555555;ext=",
    "tel:+1.7035555555;ext=1a",
    "tel:+1.7035555555;isub=1",
    "tel:+1.7035555555;phone-context=example.example",
])
def test_create_rejects_numbers_outside_the_rpp_telephone_uri(number):
    assert rejected_status(create_body(card(phones={"voice": {"number": number}}))) == 400


def test_create_splits_voice_and_fax_by_key():
    body = create_body(card(phones={
        "voice": {"number": "tel:+1.7035555555"},
        "fax": {"number": "tel:+1.7035555556", "features": {"fax": True}},
    }))

    contact = contacts.rpp_to_model(body)
    assert (contact.phone, contact.fax) == (["+1.7035555555"], ["+1.7035555556"])


@pytest.mark.parametrize("features", [None, {"voice": True}])
def test_create_accepts_a_voice_number_with_or_without_features(features):
    phone = {"number": "tel:+1.7035555555", **({"features": features} if features else {})}

    assert contacts.rpp_to_model(create_body(card(phones={"voice": phone}))).phone == ["+1.7035555555"]


def test_create_maps_authinfo():
    body = create_body(authInfo={"@type": "authInfo", "method": "authinfo", "authdata": "2fooBAR"})

    assert contacts.rpp_to_model(body).authInfo == AuthInfo(pw="2fooBAR")


def test_create_accepts_type_on_every_object():
    body = create_body(org_card(
        name={"@type": "Name", "full": "John Doe"},
        organizations={"org": {"@type": "Organization", "name": "Example Inc."}},
        addresses={"addr": {
            "@type": "Address",
            "components": [{"@type": "AddressComponent", "kind": "locality", "value": "Dulles"}],
            "countryCode": "US",
        }},
        emails={"email": {"@type": "EmailAddress", "address": "a@example.example"}},
        phones={"voice": {"@type": "Phone", "number": "tel:+1.7035555555"}},
    ))

    contact = contacts.rpp_to_model(body)
    assert (contact.name, contact.address.city) == ("John Doe", "Dulles")


VOICE = {"number": "tel:+1.7035555555"}
FAX = {"number": "tel:+1.7035555556", "features": {"fax": True}}
EMAIL = {"address": "a@example.example"}
LOCALITY = ("locality", "Dulles")


@pytest.mark.parametrize("body", [
    # Removed from the profile
    create_body(card(name={"full": "John Doe", "components": [{"kind": "given", "value": "John"}]})),
    create_body(card(name={})),
    create_body(card(addresses=address(full="1 Example Dr"))),
    create_body(card(addresses=address(LOCALITY, ("country", "USA")))),
    create_body(card(nickNames={})),
    create_body(card(emails={"email": {**EMAIL, "label": "x"}})),
    create_body(card(phones={"voice": {**VOICE, "label": "x"}})),
    create_body(card(links={"url": {"uri": "https://example.example", "pref": 1}})),
    # Organization
    create_body(card(kind="org", organizations={"org": {}})),
    # Address
    create_body(card(addresses={"addr": {"components": components(LOCALITY)}})),
    create_body(card(addresses={"addr": {"countryCode": "US"}})),
    create_body(card(addresses=address(("name", "Line 1")))),
    create_body(card(addresses=address(LOCALITY, LOCALITY))),
    create_body(card(addresses=address(LOCALITY, ("region", "A"), ("region", "B")))),
    create_body(card(addresses=address(LOCALITY, ("postcode", "1"), ("postcode", "2")))),
    # Phone features
    create_body(card(phones={"voice": {**VOICE, "features": {"text": True}}})),
    create_body(card(phones={"voice": {**VOICE, "features": {"voice": False}}})),
    # Map keys
    create_body(org_card(organizations={"a": {"name": "A"}})),
    create_body(card(addresses={"b": postal()})),
    create_body(card(emails={"a": EMAIL})),
    create_body(card(emails={"email-1": EMAIL})),
    create_body(card(emails={"email": EMAIL, "email-2": EMAIL})),
    create_body(card(emails={"email": EMAIL, "email-0": EMAIL})),
    create_body(card(emails={"email": EMAIL, "email-01": EMAIL})),
    create_body(card(phones={"a": VOICE})),
    create_body(card(phones={"voice-1": VOICE})),
    create_body(card(phones={"voice": VOICE, "voice-1": VOICE, "voice-3": VOICE})),
    create_body(card(phones={"fax-1": FAX})),
    create_body(card(links={"l": {"uri": "https://example.example"}})),
    create_body(card(links={"url": {"uri": "https://example.example", "kind": "contact"}})),
    create_body(card(links={"contact-uri": {"uri": "https://example.example"}})),
    # Key and features disagree
    create_body(card(phones={"fax": VOICE})),
    create_body(card(phones={"voice": FAX})),
    create_body(card(phones={"fax": {**VOICE, "features": {"voice": True}}})),
    # Internationalized form
    create_body(card(name={"full": "Jörg Müller"})),
    create_body(org_card(organizations={"org": {"name": "Müller GmbH"}})),
    create_body(card(addresses=address(("locality", "München")))),
    create_body(card(emails={"email": {"address": "jörg@example.example"}})),
    # Localizations
    create_body(card(localizations={"de": {"addresses/addr": postal()}})),
    create_body(card(localizations={"de": {"addresses/addr/countryCode": "DE"}})),
    create_body(card(localizations={"de": {"phones": {"voice": VOICE}}})),
    create_body(card(localizations={"de": {"name": None}})),
    create_body(card(localizations={"not a tag!": {"name": {"full": "Name"}}})),
    create_body(card(language="not a tag!")),
])
def test_create_rejects_what_the_profile_does_not_allow(body):
    assert rejected_status(body) == 400


@pytest.mark.parametrize("body", [
    create_body(card(organizations={"org": {"name": "Example Inc."}})),
    create_body(card(links={"url": {"uri": "https://example.example"}})),
    create_body(card(links={"contact-uri": {"uri": "https://example.example", "kind": "contact"}})),
    create_body(card(emails={"email": EMAIL, "email-1": EMAIL})),
    create_body(card(phones={"voice": VOICE, "voice-1": VOICE})),
    create_body(card(phones={"fax": FAX, "fax-1": FAX})),
    create_body(card(phones={"voice": {**VOICE, "features": {"voice": True, "fax": True}}})),
    create_body(card(addresses=address(("name", "1"), ("name", "2"), ("name", "3"), ("name", "4"), LOCALITY))),
    create_body(card(localizations={"de": {"emails": {"email": EMAIL}}})),
    create_body(card(localizations={"de": {"organizations": {"org": {"name": "Example GmbH"}}}})),
    create_body(card(localizations={"de": {"name": {"full": "A"}}, "fr": {"name": {"full": "B"}}})),
    create_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited"}]),
    create_body(disclose={"@type": "disclose"}),
    create_body(authInfo={"@type": "authInfo", "method": "other", "authdata": "x"}),
])
def test_create_rejects_what_the_model_cannot_hold(body):
    assert rejected_status(body) == 501


def test_create_rejects_a_profile_violation_before_what_the_model_cannot_hold():
    assert rejected_status(create_body(card(emails={"email": EMAIL, "email-1": EMAIL, "email-3": EMAIL}))) == 400


def test_create_accepts_language():
    assert contacts.rpp_to_model(create_body(card(language="en"))).name == "John Doe"


def test_create_without_localizations_has_no_localized_form():
    assert contacts.rpp_to_model(create_body()).localizedPostalInfo is None


def test_create_empty_localization_has_no_localized_form():
    assert contacts.rpp_to_model(create_body(card(localizations={"de": {}}))).localizedPostalInfo is None


def test_create_maps_a_full_localization():
    body = create_body(org_card(addresses=address(LOCALITY), localizations={"de": {
        "name": {"full": "Jörg Müller"},
        "organizations": {"org": {"name": "Müller GmbH"}},
        "addresses": {"addr": {"components": components(("locality", "München")), "countryCode": "DE"}},
    }}))

    assert contacts.rpp_to_model(body).localizedPostalInfo == LocalizedPostalInfo(
        name="Jörg Müller",
        organisationName="Müller GmbH",
        address=Address(street=None, city="München", country="DE"),
    )


def test_create_partial_localization_inherits_the_internationalized_form():
    body = create_body(org_card(addresses=address(LOCALITY), localizations={"de": {
        "addresses": {"addr": {"components": components(("locality", "München")), "countryCode": "DE"}},
    }}))

    assert contacts.rpp_to_model(body).localizedPostalInfo == LocalizedPostalInfo(
        name="John Doe",
        organisationName="Example Inc.",
        address=Address(street=None, city="München", country="DE"),
    )


def test_create_localization_inherits_the_address():
    body = create_body(card(addresses=address(LOCALITY), localizations={"de": {"name": {"full": "Jörg"}}}))

    localized = contacts.rpp_to_model(body).localizedPostalInfo
    assert (localized.name, localized.address.city) == ("Jörg", "Dulles")


def test_create_limits_street_lines_in_a_localization():
    lines = [("name", "1"), ("name", "2"), ("name", "3"), ("name", "4"), LOCALITY]
    body = create_body(card(localizations={"de": {"addresses": address(*lines)}}))

    assert rejected_status(body) == 501


FIGURE_2 = {
    "@type": "Card",
    "version": "2.0",
    "language": "en",
    "name": {"full": "Joe User"},
    "organizations": {"org": {"name": "Example Org"}},
    "addresses": {"addr": {
        "components": components(
            ("name", "Main Street 1"), ("locality", "Ludwigshafen am Rhein"),
            ("region", "Rhineland-Palatinate"), ("postcode", "67067"),
        ),
        "countryCode": "DE",
    }},
    "emails": {"email": {"address": "joe.user@example.com"}, "email-1": {"address": "joe@example.net"}},
    "phones": {
        "voice": {"features": {"voice": True}, "number": "tel:+49.6215550100"},
        "voice-1": {"number": "tel:+49.6215550101;ext=1234"},
        "fax": {"features": {"fax": True}, "number": "tel:+49.6215550199"},
    },
    "localizations": {"de": {"addresses": {"addr": {
        "components": components(
            ("name", "Hauptstrasse 1"), ("locality", "Ludwigshafen am Rhein"),
            ("region", "Rheinland-Pfalz"), ("postcode", "67067"),
        ),
        "countryCode": "DE",
    }}}},
}


def test_draft_figure_2_is_valid():
    validate_schema("Card", FIGURE_2)


def test_draft_figure_2_fails_only_on_the_additional_entries():
    assert rejected_status(create_body(copy.deepcopy(FIGURE_2))) == 501


def test_draft_figure_2_maps_without_the_additional_entries():
    figure = copy.deepcopy(FIGURE_2)
    figure["kind"] = "org"
    del figure["emails"]["email-1"], figure["phones"]["voice-1"]

    contact = contacts.rpp_to_model(create_body(figure))

    assert contact.localizedPostalInfo == LocalizedPostalInfo(
        name="Joe User",
        organisationName="Example Org",
        address=Address(
            street=["Hauptstrasse 1"], city="Ludwigshafen am Rhein", stateProvince="Rheinland-Pfalz",
            postalCode="67067", country="DE",
        ),
    )


def test_read_builds_the_card():
    rpp = contacts.model_to_rpp(info_contact(
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
            "voice": {"number": "tel:+1.7035555555;ext=12"},
            "fax": {"number": "tel:+1.7035555556", "features": {"fax": True}},
        },
        "emails": {"email": {"address": "jdoe@example.example"}},
    }


def test_read_maps_org_kind():
    rpp = contacts.model_to_rpp(info_contact(type=ContactType.ORG, organisationName="Example Inc."))

    assert rpp["contactInfo"]["kind"] == "org"
    assert rpp["contactInfo"]["organizations"] == {"org": {"name": "Example Inc."}}


def test_read_leaves_out_kind_when_undefined():
    assert "kind" not in contacts.model_to_rpp(info_contact(type=ContactType.UNDEFINED))["contactInfo"]


def test_read_maps_metadata_and_status():
    rpp = contacts.model_to_rpp(info_contact(crID="ClientY"))

    assert rpp["@type"] == "contact"
    assert rpp["provMetadata"] == {"@type": "provMetadata", "spClientId": "ClientX", "crClientId": "ClientY"}
    assert rpp["status"] == [{"@type": "contactStatus", "label": "ok"}]


DULLES = Address(street=None, city="Dulles", country="US")
MUNICH = Address(street=None, city="München", country="DE")
MUNICH_RPP = {"components": components(("locality", "München")), "countryCode": "DE"}


def test_read_without_a_localized_form_has_no_localizations():
    assert "localizations" not in contacts.model_to_rpp(info_contact(address=DULLES))["contactInfo"]


def test_read_returns_the_localized_form_as_undetermined_language():
    rpp = contacts.model_to_rpp(info_contact(
        type=ContactType.ORG, organisationName="Example Inc.", address=DULLES,
        localizedPostalInfo=LocalizedPostalInfo(name="Jörg", organisationName="Müller GmbH", address=MUNICH),
    ))

    assert rpp["contactInfo"]["localizations"] == {"und": {
        "name": {"full": "Jörg"},
        "organizations": {"org": {"name": "Müller GmbH"}},
        "addresses": {"addr": MUNICH_RPP},
    }}


def test_read_returns_only_members_that_differ():
    rpp = contacts.model_to_rpp(info_contact(
        address=DULLES, localizedPostalInfo=LocalizedPostalInfo(name="John Doe", address=MUNICH),
    ))

    assert rpp["contactInfo"]["localizations"] == {"und": {"addresses": {"addr": MUNICH_RPP}}}


def test_read_identical_localized_form_has_no_localizations():
    rpp = contacts.model_to_rpp(info_contact(
        address=DULLES, localizedPostalInfo=LocalizedPostalInfo(name="John Doe", address=DULLES),
    ))

    assert "localizations" not in rpp["contactInfo"]


def test_read_localized_only_contact_has_no_internationalized_form():
    rpp = contacts.model_to_rpp(info_contact(
        name=None, localizedPostalInfo=LocalizedPostalInfo(name="Jörg", address=MUNICH),
    ))

    assert "name" not in rpp["contactInfo"] and "addresses" not in rpp["contactInfo"]
    assert rpp["contactInfo"]["localizations"] == {"und": {
        "name": {"full": "Jörg"}, "addresses": {"addr": MUNICH_RPP},
    }}
