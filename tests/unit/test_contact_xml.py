from models import Address, Contact, ContactType, LocalizedPostalInfo
from epp_to_model_mapper import contact_check_xml, create_contact_xml, parse_contact_check_response, parse_contact_response

CONTACT_NS = 'xmlns:contact="urn:ietf:params:xml:ns:contact-1.0"'


def postal(kind, name, city, org=""):
    return (
        f'<contact:postalInfo type="{kind}"><contact:name>{name}</contact:name>{org}'
        f'<contact:addr><contact:city>{city}</contact:city><contact:cc>DE</contact:cc></contact:addr>'
        '</contact:postalInfo>'
    )


def info_reply(*postal_infos):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        '<result code="1000"><msg>Command completed successfully</msg></result>'
        f'<resData><contact:infData {CONTACT_NS}><contact:id>JD-1</contact:id><contact:roid>R-1</contact:roid>'
        f'<contact:status s="ok"/>{"".join(postal_infos)}<contact:email>a@example.example</contact:email>'
        '<contact:clID>ClientX</contact:clID><contact:crID>ClientX</contact:crID>'
        '<contact:crDate>2026-01-01T00:00:00.0Z</contact:crDate></contact:infData></resData>'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def contact(**extra):
    return Contact(
        id="JD-1", type=ContactType.PERSON, name="Joe",
        address=Address(street=None, city="Berlin", country="DE"), **extra,
    )


def test_create_sends_only_the_int_form_without_a_localization():
    xml = create_contact_xml(contact(), client_request_id="cl-1")

    assert 'type="int"' in xml and 'type="loc"' not in xml


def test_create_sends_the_loc_form_after_the_int_form():
    xml = create_contact_xml(contact(localizedPostalInfo=LocalizedPostalInfo(
        name="Jörg", address=Address(street=None, city="München", country="DE"),
    )), client_request_id="cl-1")

    assert xml.index('type="int"') < xml.index('type="loc"')
    loc = xml[xml.index('type="loc"'):]
    assert "Jörg" in loc and "München" in loc


def test_create_sends_the_org_in_the_loc_form():
    xml = create_contact_xml(Contact(
        id="JD-1", type=ContactType.ORG, name="Joe", organisationName="Example Inc.",
        localizedPostalInfo=LocalizedPostalInfo(name="Joe", organisationName="Müller GmbH"),
    ), client_request_id="cl-1")

    assert "Müller GmbH" in xml[xml.index('type="loc"'):]


def test_parse_reads_the_int_form_only():
    parsed = parse_contact_response(info_reply(postal("int", "Joe", "Berlin")), "cl-1").contact

    assert (parsed.name, parsed.address.city, parsed.localizedPostalInfo) == ("Joe", "Berlin", None)


def test_parse_reads_both_forms_whatever_their_order():
    parsed = parse_contact_response(
        info_reply(postal("loc", "Jörg", "München"), postal("int", "Joe", "Berlin")), "cl-1",
    ).contact

    assert (parsed.name, parsed.address.city) == ("Joe", "Berlin")
    assert parsed.localizedPostalInfo == LocalizedPostalInfo(
        name="Jörg", address=Address(street=None, city="München", country="DE"),
    )


def test_parse_keeps_a_loc_only_contact_out_of_the_int_form():
    parsed = parse_contact_response(info_reply(postal("loc", "Jörg", "München")), "cl-1").contact

    assert (parsed.name, parsed.address, parsed.type) == (None, None, ContactType.PERSON)
    assert parsed.localizedPostalInfo.name == "Jörg"


def test_parse_loc_only_org():
    org = "<contact:org>Müller GmbH</contact:org>"

    parsed = parse_contact_response(info_reply(postal("loc", "Jörg", "München", org)), "cl-1").contact

    assert parsed.type == ContactType.ORG
    assert parsed.localizedPostalInfo.organisationName == "Müller GmbH"


def test_parse_reads_the_repository():
    assert parse_contact_response(info_reply(), "cl-1").contact.roid == "R-1"


def test_parse_reads_the_update_client():
    xml = info_reply().replace("</contact:crDate>", "</contact:crDate><contact:upID>ClientY</contact:upID>")

    assert parse_contact_response(xml, "cl-1").contact.upID == "ClientY"


def check_reply(avail, reason=""):
    return (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        '<result code="1000"><msg>Command completed successfully</msg></result>'
        f'<resData><contact:chkData {CONTACT_NS}><contact:cd><contact:id avail="{avail}">JD-1</contact:id>{reason}'
        '</contact:cd></contact:chkData></resData>'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )


def test_check_xml():
    xml = contact_check_xml("jd-1", client_request_id="cl-1")

    assert "<contact:check" in xml
    assert "<contact:id>jd-1</contact:id>" in xml
    assert "cl-1" in xml


def test_parse_check_available():
    response = parse_contact_check_response(check_reply(1), "jd-1", "cl-1")

    assert response.available is True
    assert response.reason is None
    assert response.contact_id == "jd-1"
    assert response.server_transaction_id == "sv-1"


def test_parse_check_taken_gives_the_reason():
    response = parse_contact_check_response(check_reply(0, "<contact:reason>In use</contact:reason>"), "jd-1", "cl-1")

    assert response.available is False
    assert response.reason == "In use"
