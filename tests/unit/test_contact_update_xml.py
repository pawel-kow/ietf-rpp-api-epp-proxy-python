from registry_adapter.epp.commands.contact.contact_xml import (
    parse_contact_response, parse_contact_update_response, update_contact_xml,
)
from models import (
    Address, AuthInfo, ContactUpdate, ContactUpdateChange, ContactUpdateChanges, PostalInfoChange,
)
from tests.unit.test_contact_xml import info_reply, postal
from tests.helper.epp_ns_map import EPP_NS_MAP

ADDRESS = Address(street=["1 Main"], city="Berlin", stateProvince="BE", postalCode="10115", country="DE")


def xml(**members):
    return update_contact_xml(ContactUpdate(id="JD-1", **members), client_request_id="cl-1", ns_map=EPP_NS_MAP)


def test_status_is_added_and_removed_with_its_reason():
    text = xml(
        add=ContactUpdateChanges(status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "why"}),
        remove=ContactUpdateChanges(status=["clientDeleteProhibited"]),
    )

    assert '<contact:status s="clientUpdateProhibited" lang="en">why</contact:status>' in text.replace("\n", "")
    assert 'contact:rem' in text and 'clientDeleteProhibited' in text
    assert "<contact:chg" not in text


def test_a_changed_form_is_sent_complete():
    text = xml(change=ContactUpdateChange(postal_info=[
        PostalInfoChange(form="int", name="Joe Doe", organisationName="ACME", address=ADDRESS),
    ]))

    assert 'type="int"' in text
    for part in ("Joe Doe", "ACME", "1 Main", "Berlin", "BE", "10115", "DE"):
        assert part in text


def test_an_empty_organisation_clears_it_with_an_empty_element():
    text = xml(change=ContactUpdateChange(postal_info=[
        PostalInfoChange(form="loc", name="Joe", organisationName="", address=ADDRESS),
    ]))

    assert "<contact:org></contact:org>" in text or "<contact:org/>" in text


def test_a_form_without_an_organisation_sends_none():
    text = xml(change=ContactUpdateChange(postal_info=[
        PostalInfoChange(form="int", name="Joe", address=ADDRESS),
    ]))

    assert "contact:org" not in text


def test_empty_voice_and_fax_clear_the_numbers():
    text = xml(change=ContactUpdateChange(voice="", fax=""))

    assert "<contact:voice></contact:voice>" in text or "<contact:voice/>" in text
    assert "<contact:fax></contact:fax>" in text or "<contact:fax/>" in text


def test_numbers_keep_their_extension_and_email_and_auth_info_are_sent():
    text = xml(change=ContactUpdateChange(
        voice="+49.123x12", email="a@example.example", authInfo=AuthInfo(pw="Secret1!x"),
    ))

    assert 'x="12"' in text and "+49.123" in text
    assert "a@example.example" in text and "Secret1!x" in text


def test_the_update_reply_carries_the_transaction_ids():
    reply = (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response><result code="1000"><msg>ok</msg></result>'
        '<trID><clTRID>cl-1</clTRID><svTRID>sv-1</svTRID></trID></response></epp>'
    )

    response = parse_contact_update_response(reply, "cl-1")

    assert response.server_transaction_id == "sv-1" and response.client_transaction_id == "cl-1"


def test_info_reads_a_status_reason_but_not_the_repeated_label():
    reply = info_reply(postal("int", "Joe", "Berlin")).replace(
        '<contact:status s="ok"/>',
        '<contact:status s="ok">ok</contact:status><contact:status s="clientUpdateProhibited">why</contact:status>',
    )

    contact = parse_contact_response(reply, "cl-1").contact

    assert contact.status_reasons == {"clientUpdateProhibited": "why"}


def test_info_reads_empty_address_members_as_absent():
    reply = info_reply(
        '<contact:postalInfo type="int"><contact:name>Joe</contact:name><contact:org></contact:org>'
        '<contact:addr><contact:street>1 Main</contact:street><contact:city>Berlin</contact:city>'
        '<contact:sp></contact:sp><contact:pc></contact:pc><contact:cc>DE</contact:cc></contact:addr>'
        '</contact:postalInfo>'
    )

    contact = parse_contact_response(reply, "cl-1").contact

    assert contact.address == Address(street=["1 Main"], city="Berlin", country="DE")
