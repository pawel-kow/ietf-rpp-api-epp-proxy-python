from eppclient.epp_backend import EppBackend
from flows import patch_contact, replace_contact
from models import (
    Address, Contact, ContactReplacement, ContactUpdate, ContactUpdateChange, ErrorResponse, PostalInfoChange, ResultCode,
    LocalizedPostalInfo, contact_application,
)
from tests.helper.fake_epp_client import FakeEppClient
from tests.unit.test_contact_xml import info_reply, postal

ID = "JD-1"
EMAIL_CHANGE = ContactUpdate(id=ID, change=ContactUpdateChange(email="b@example.example"))
BERLIN = Address(street=None, city="Berlin", country="DE")
# The contact of `info()`.
UNCHANGED = ContactReplacement(id=ID, name="Joe", address=BERLIN, email=["a@example.example"])


def applying(update: ContactUpdate):
    """The patch that asks for the current contact with `update` applied."""
    return lambda contact: contact_application.apply(contact, update)


def reply(code, res_data=""):
    return (code < 2000, str(code), (
        '<epp xmlns="urn:ietf:params:xml:ns:epp-1.0"><response>'
        f'<result code="{code}"><msg>Message</msg></result>{res_data}'
        '<trID><svTRID>sv-1</svTRID></trID></response></epp>'
    ))


def info(sponsor="ClientX"):
    xml = info_reply(postal("int", "Joe", "Berlin")).replace("<contact:clID>ClientX", f"<contact:clID>{sponsor}")
    return (True, "1000", xml)


DONE = reply(1000)
MISSING = reply(2303)


def client(*replies, username="ClientX"):
    return FakeEppClient(username, "p", replies=replies)


def never_called(contact: Contact):
    raise AssertionError("the patch needs no current contact")


def kinds(epp):
    return [("contact:info" in m, "contact:update" in m) for m in epp.sent]


def test_a_direct_update_is_not_preceded_by_a_read():
    epp = client(DONE, info())

    result = patch_contact(EppBackend(epp), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert kinds(epp) == [(False, True), (True, False)]
    assert result.contact.id == "JD-1"


def test_a_patch_needing_the_contact_reads_it_first():
    epp = client(info(), DONE, info())
    seen = []

    def from_current(contact):
        seen.append(contact)
        return contact_application.apply(contact, EMAIL_CHANGE)

    result = patch_contact(EppBackend(epp), ID, None, from_current, "cl-1")

    assert seen[0].name == "Joe"
    assert kinds(epp) == [(True, False), (False, True), (True, False)]
    assert "<contact:email>b@example.example</contact:email>" in epp.sent[1]
    assert result.mutation.server_transaction_id == "sv-1"


def test_a_failed_read_is_returned():
    assert isinstance(patch_contact(EppBackend(client(MISSING)), ID, None, never_called, "cl-1"), ErrorResponse)


def test_a_failed_update_is_returned():
    result = patch_contact(EppBackend(client(reply(2201))), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.AUTHORIZATION_ERROR


def test_a_replacement_that_changes_nothing_sends_no_update():
    epp = client(info())

    result = replace_contact(EppBackend(epp), UNCHANGED, "cl-1")

    assert kinds(epp) == [(True, False)]
    assert result.contact.id == "JD-1" and result.mutation.server_transaction_id == "sv-1"


def test_an_unchanged_contact_of_another_client_is_a_403():
    result = replace_contact(EppBackend(client(info("ClientY"))), UNCHANGED, "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.AUTHORIZATION_ERROR
    assert result.client_transaction_id == "cl-1"


def test_the_sponsor_is_compared_without_regard_to_case():
    result = replace_contact(EppBackend(client(info(), username="clientx")), UNCHANGED, "cl-1")

    assert result.contact is not None


def test_a_failed_read_back_leaves_the_mutation_without_a_contact():
    result = patch_contact(EppBackend(client(DONE, MISSING)), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert result.contact is None and result.mutation.server_transaction_id == "sv-1"


def test_a_read_back_that_raises_leaves_the_mutation_without_a_contact():
    result = patch_contact(EppBackend(client(DONE, ConnectionError())), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert result.contact is None


LOC_FORM = PostalInfoChange(form="loc", name="Jörg", address=Address(street=None, city="Berlin", country="DE"))
INT_FORM = PostalInfoChange(form="int", name="Joe", address=Address(street=None, city="Berlin", country="DE"))
ADD_LOC = ContactUpdate(id=ID, change=ContactUpdateChange(postal_info=[LOC_FORM]))
ADD_INT = ContactUpdate(id=ID, change=ContactUpdateChange(postal_info=[INT_FORM]))


def info_with(*forms):
    return (True, "1000", info_reply(*forms))


INT_ONLY = info_with(postal("int", "Joe", "Berlin"))
LOC_ONLY = info_with(postal("loc", "Jörg", "Berlin"))
BOTH = info_with(postal("int", "Joe", "Berlin"), postal("loc", "Jörg", "Berlin"))


def test_a_form_the_registry_did_not_add_is_an_error_naming_it():
    result = patch_contact(EppBackend(client(INT_ONLY, DONE, INT_ONLY)), ID, None, applying(ADD_LOC), "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.COMMAND_FAILED
    assert "loc" in result.msg
    assert result.server_transaction_id == "sv-1" and result.client_transaction_id == "cl-1"


def test_an_int_form_the_registry_did_not_add_to_a_loc_only_contact_is_an_error():
    result = patch_contact(EppBackend(client(LOC_ONLY, DONE, LOC_ONLY)), ID, None, applying(ADD_INT), "cl-1")

    assert isinstance(result, ErrorResponse) and "int" in result.msg


def test_a_form_the_registry_added_is_a_success():
    result = patch_contact(EppBackend(client(INT_ONLY, DONE, BOTH)), ID, None, applying(ADD_LOC), "cl-1")

    assert result.contact is not None


def test_a_form_that_was_there_and_is_changed_is_not_checked():
    changed = ContactReplacement(
        id=ID, name="Joe", address=BERLIN, email=["a@example.example"],
        localizedPostalInfo=LocalizedPostalInfo(name="Jörgen", address=BERLIN),
    )

    result = replace_contact(EppBackend(client(BOTH, DONE, BOTH)), changed, "cl-1")

    assert result.contact is not None


def test_a_form_that_cannot_be_read_back_is_not_an_error():
    result = patch_contact(EppBackend(client(INT_ONLY, DONE, MISSING)), ID, None, applying(ADD_LOC), "cl-1")

    assert result.contact is None


def test_a_direct_update_has_nothing_to_compare_with():
    result = patch_contact(EppBackend(client(DONE, INT_ONLY)), ID, ADD_LOC, never_called, "cl-1")

    assert result.contact is not None
