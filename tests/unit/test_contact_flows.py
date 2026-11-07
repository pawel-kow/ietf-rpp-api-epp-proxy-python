from flows import patch_contact, replace_contact
from models import Contact, ContactUpdate, ContactUpdateChange, ErrorResponse, ResultCode
from tests.helper.fake_epp_client import FakeEppClient
from tests.unit.test_contact_xml import info_reply, postal

ID = "JD-1"
EMAIL_CHANGE = ContactUpdate(id=ID, change=ContactUpdateChange(email="b@example.example"))


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

    result = patch_contact(epp, ID, EMAIL_CHANGE, never_called, "cl-1")

    assert kinds(epp) == [(False, True), (True, False)]
    assert result.contact.id == "JD-1"


def test_a_patch_needing_the_contact_reads_it_first():
    epp = client(info(), DONE, info())
    seen = []

    def from_current(contact):
        seen.append(contact)
        return EMAIL_CHANGE

    result = patch_contact(epp, ID, None, from_current, "cl-1")

    assert seen[0].name == "Joe"
    assert kinds(epp) == [(True, False), (False, True), (True, False)]
    assert result.mutation.server_transaction_id == "sv-1"


def test_a_failed_read_is_returned():
    assert isinstance(patch_contact(client(MISSING), ID, None, never_called, "cl-1"), ErrorResponse)


def test_a_failed_update_is_returned():
    result = patch_contact(client(reply(2201)), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.AUTHORIZATION_ERROR


def test_a_replacement_that_changes_nothing_sends_no_update():
    epp = client(info())

    result = replace_contact(epp, ID, lambda contact: ContactUpdate(id=ID), "cl-1")

    assert kinds(epp) == [(True, False)]
    assert result.contact.id == "JD-1" and result.mutation.server_transaction_id == "sv-1"


def test_an_unchanged_contact_of_another_client_is_a_403():
    result = replace_contact(client(info("ClientY")), ID, lambda contact: ContactUpdate(id=ID), "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.AUTHORIZATION_ERROR
    assert result.client_transaction_id == "cl-1"


def test_the_sponsor_is_compared_without_regard_to_case():
    result = replace_contact(client(info(), username="clientx"), ID, lambda contact: ContactUpdate(id=ID), "cl-1")

    assert result.contact is not None


def test_a_failed_read_back_leaves_the_mutation_without_a_contact():
    result = patch_contact(client(DONE, MISSING), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert result.contact is None and result.mutation.server_transaction_id == "sv-1"


def test_a_read_back_that_raises_leaves_the_mutation_without_a_contact():
    result = patch_contact(client(DONE, ConnectionError()), ID, EMAIL_CHANGE, never_called, "cl-1")

    assert result.contact is None
