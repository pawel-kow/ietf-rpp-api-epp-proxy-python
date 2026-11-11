import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from models import ContactType
from rpp_to_model_mapper import contact_patch
from tests.helper.contact_fixtures import ADDRESS, current_contact, derived_update, localized

ID = "JD-1234"
STATUS = {"@type": "contactStatus", "label": "clientUpdateProhibited"}


def op(name, path, **members):
    return {"op": name, "path": path, **members}


def direct(*operations):
    return map_request(contact_patch.rpp_to_model, ID, list(operations))


def with_current(*operations, current=None):
    current = current or current_contact()
    return derived_update(current, map_request(contact_patch.rpp_to_model_with_current, ID, list(operations), current))


def rejected(*operations, current=None) -> ProblemException:
    with pytest.raises(ProblemException) as problem:
        with_current(*operations, current=current) if direct(*operations) is None else direct(*operations)
    return problem.value


def status_of(*operations, current=None) -> int:
    return rejected(*operations, current=current).status


def test_add_status_goes_without_a_read():
    update = direct(op("add", "/status", value={**STATUS, "reason": "why"}))

    assert update.add.status == ["clientUpdateProhibited"] and update.add.status_reasons == {"clientUpdateProhibited": "why"}


def test_remove_client_status_by_label_goes_without_a_read():
    update = direct(op("remove", "/status", match={"label": "clientUpdateProhibited"}))

    assert update.remove.status == ["clientUpdateProhibited"]


def test_replace_auth_info_goes_without_a_read():
    value = {"@type": "authInfo", "method": "authinfo", "authdata": "NewSecret1!x"}

    assert direct(op("replace", "/authInfo", value=value)).change.authInfo.pw == "NewSecret1!x"


def test_remove_auth_info_is_a_501():
    assert status_of(op("remove", "/authInfo")) == 501


@pytest.mark.parametrize("operation", [
    op("replace", "/contactInfo/name/full", value="Jo"),
    op("remove", "/contactInfo/emails/email"),
    op("remove", "/contactInfo/phones/voice"),
    op("add", "/contactInfo/phones/voice-1", value={"number": "tel:+49.1"}),
    op("remove", "/contactInfo/phones"),
    op("remove", "/status"),
    op("remove", "/status", match={"label": "clientUpdateProhibited", "reason": "x"}),
    op("replace", "/status", value=[STATUS]),
])
def test_these_need_the_current_contact(operation):
    assert direct(operation) is None


@pytest.mark.parametrize("operation, member, value", [
    (op("replace", "/contactInfo/emails/email/address", value="b@example.example"), "email", "b@example.example"),
    (op("replace", "/contactInfo/emails/email", value={"address": "b@example.example"}), "email", "b@example.example"),
    (op("replace", "/contactInfo/phones/voice/number", value="tel:+49.999"), "voice", "+49.999"),
    (op("add", "/contactInfo/phones/voice", value={"number": "tel:+49.999;ext=7"}), "voice", "+49.999x7"),
    (op("replace", "/contactInfo/phones/fax/number", value="tel:+49.888"), "fax", "+49.888"),
    (op("add", "/contactInfo/phones/fax", value={"number": "tel:+49.888", "features": {"fax": True}}), "fax", "+49.888"),
])
def test_a_phone_or_the_email_goes_without_a_read(operation, member, value):
    """EPP holds one value each, which `chg` sets (#108)."""
    update = direct(operation)

    assert getattr(update.change, member) == value
    assert update.change.postal_info == [] and update.add is None and update.remove is None


def test_the_last_operation_on_a_number_wins():
    update = direct(op("replace", "/contactInfo/phones/voice/number", value="tel:+49.2"), op("add", "/contactInfo/phones/voice", value={"number": "tel:+49.1"}))

    assert update.change.voice == "+49.1"


@pytest.mark.parametrize("operation", [
    op("replace", "/contactInfo/emails/email/address", value="bé@example.example"),
    op("add", "/contactInfo/phones/fax", value={"number": "tel:+49.888"}),
    op("add", "/contactInfo/phones/voice", value={"number": "tel:+49.888", "features": {"fax": True}}),
    op("replace", "/contactInfo/phones/voice/number", value="+49.888"),
    op("add", "/contactInfo/phones/voice", value={"number": "tel:+49.888", "foo": 1}),
])
def test_a_direct_phone_or_email_is_checked_as_in_a_full_update(operation):
    assert status_of(operation) == 400


def test_a_phone_with_voice_and_fax_is_a_501():
    assert status_of(op("add", "/contactInfo/phones/voice", value={"number": "tel:+49.8", "features": {"voice": True, "fax": True}})) == 501


@pytest.mark.parametrize("operation", [
    op("replace", "/id", value="X"), op("replace", "/provMetadata", value={}), op("copy", "/status"),
    op("replace", "/processes", value={}),
])
def test_a_path_or_operation_outside_the_update_is_a_400(operation):
    assert status_of(operation) == 400


def test_a_new_email_is_a_change():
    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"))

    assert update.change.email == "b@example.example" and update.change.postal_info == []


def test_a_patch_that_changes_nothing_gives_an_empty_update():
    update = with_current(op("replace", "/contactInfo/emails/email/address", value="a@example.example"))

    assert update.add is None and update.remove is None and update.change is None


def test_removing_the_organisation_clears_it_and_the_kind_follows():
    current = current_contact(type=ContactType.ORG, organisationName="ACME Inc.")

    update = with_current(op("remove", "/contactInfo/organizations/org"), current=current)

    (form,) = update.change.postal_info
    assert (form.name, form.organisationName, form.address) == ("John Doe", "", ADDRESS)


def test_adding_an_organisation_makes_the_contact_an_org():
    update = with_current(op("add", "/contactInfo/organizations", value={"org": {"name": "ACME Inc."}}))

    (form,) = update.change.postal_info
    assert form.organisationName == "ACME Inc."


def test_a_kind_the_patch_names_is_kept():
    current = current_contact(type=ContactType.ORG, organisationName="ACME Inc.")

    assert status_of(op("remove", "/contactInfo/organizations/org"), op("replace", "/contactInfo/kind", value="org"), current=current) == 400


def test_removing_a_missing_organisation_is_a_422():
    problem = rejected(op("remove", "/contactInfo/organizations/org"))

    assert problem.status == 422


def test_removing_a_number_clears_it():
    update = with_current(op("remove", "/contactInfo/phones/voice"))

    assert update.change.voice == "" and update.change.fax is None


def test_adding_a_number_to_a_contact_without_phones():
    update = with_current(
        op("add", "/contactInfo/phones/voice", value={"number": "tel:+49.999"}),
        current=current_contact(phone=None, fax=None),
    )

    assert update.change.voice == "+49.999"


@pytest.mark.parametrize("path", [
    "/contactInfo/name", "/contactInfo/addresses", "/contactInfo/emails/email", "/contactInfo/emails",
])
def test_removing_what_epp_cannot_clear_is_a_501(path):
    assert status_of(op("remove", path)) == 501


def test_removing_a_visible_localization_is_a_501():
    current = current_contact(localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    assert status_of(op("remove", "/contactInfo/localizations"), current=current) == 501


def test_a_patch_leaves_a_localization_alone():
    current = current_contact(localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"), current=current)

    assert [f.form for f in update.change.postal_info] == []


def test_an_invisible_localization_follows_a_changed_name():
    current = current_contact(localizedPostalInfo=localized(name="John Doe", address=ADDRESS))

    update = with_current(op("replace", "/contactInfo/name/full", value="Joe Doe"), current=current)

    assert {f.form: f.name for f in update.change.postal_info} == {"int": "Joe Doe", "loc": "Joe Doe"}


def test_a_localization_added_by_a_patch_is_sent_complete():
    update = with_current(op("add", "/contactInfo/localizations", value={"de": {"name": {"full": "Jörg"}}}))

    assert [(f.form, f.name, f.address) for f in update.change.postal_info] == [("loc", "Jörg", ADDRESS)]


def test_replace_status_with_a_client_status():
    update = with_current(op("replace", "/status", value=[STATUS]))

    assert update.add.status == ["clientUpdateProhibited"] and update.remove is None


def test_remove_status_clears_the_client_statuses_and_keeps_server_ones():
    current = current_contact(status=["clientDeleteProhibited", "serverUpdateProhibited"])

    update = with_current(op("remove", "/status"), current=current)

    assert update.remove.status == ["clientDeleteProhibited"]


def test_a_value_naming_a_server_status_is_a_400():
    assert status_of(op("replace", "/status", value=[{"@type": "contactStatus", "label": "serverUpdateProhibited"}])) == 400


@pytest.mark.parametrize("operation", [
    op("replace", "/contactInfo", value={"@type": "Card", "version": "2.0", "name": {"full": "X"}, "foo": 1}),
    op("replace", "/contactInfo/name", value={"full": "X", "foo": 1}),
    op("add", "/contactInfo/emails/email-1", value={"address": "c@example.example", "foo": 1}),
    op("replace", "/status", value=[{**STATUS, "foo": 1}]),
])
def test_an_undeclared_nested_member_is_a_400(operation):
    assert status_of(operation) == 400


def test_disclose_is_a_501():
    assert status_of(op("add", "/disclose", value={"@type": "disclose"})) == 501


def test_auth_info_operations_are_applied_with_a_read_too():
    value = {"@type": "authInfo", "method": "authinfo", "authdata": "NewSecret1!x"}

    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"), op("replace", "/authInfo", value=value))

    assert update.change.authInfo.pw == "NewSecret1!x" and update.change.email == "b@example.example"


def test_an_unchanged_auth_info_is_not_sent():
    assert with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example")).change.authInfo is None


def test_a_localization_cannot_lose_its_name_or_address_on_a_contact_with_only_that_form():
    current = current_contact(name=None, address=None, localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    assert status_of(op("remove", "/contactInfo/localizations/und/name"), current=current) == 501
    assert status_of(op("remove", "/contactInfo/localizations/und/addresses"), current=current) == 501


def test_a_localization_the_read_hides_in_part_is_left_alone():
    """The loc has no organisation, the card has one, and the read shows nothing of it."""
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.", localizedPostalInfo=localized(name="John Doe", address=ADDRESS),
    )

    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"), current=current)

    assert update.change.postal_info == []


def test_a_localization_the_read_shows_in_part_is_not_given_the_organisation_of_the_card():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.", localizedPostalInfo=localized(name="Yohn", address=ADDRESS),
    )

    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"), current=current)

    assert update.change.postal_info == []


STORED = dict(status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "why"})


def test_a_stored_status_reason_is_not_changed_by_another_patch():
    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"), current=current_contact(**STORED))

    assert update.add is None and update.remove is None


def test_replacing_a_status_with_its_stored_reason_changes_nothing():
    value = [{**STATUS, "reason": "why"}]

    update = with_current(op("replace", "/status", value=value), current=current_contact(**STORED))

    assert update.add is None and update.remove is None


def test_a_server_status_with_a_stored_text_is_not_touched():
    current = current_contact(status=["ok"], status_reasons={"ok": "all fine"})

    update = with_current(op("replace", "/contactInfo/emails/email/address", value="b@example.example"), current=current)

    assert update.add is None and update.remove is None


@pytest.mark.parametrize("operations", [
    [op("add", "/status", value=STATUS), op("remove", "/status", match={"label": "clientUpdateProhibited"})],
    [op("remove", "/status", match={"label": "clientUpdateProhibited"}), op("add", "/status", value=STATUS)],
])
def test_two_operations_on_one_status_need_the_current_contact_to_keep_their_order(operations):
    assert direct(*operations) is None


def test_an_added_status_that_is_removed_again_is_no_change():
    update = with_current(
        op("add", "/status", value=STATUS), op("remove", "/status", match={"label": "clientUpdateProhibited"}),
    )

    assert update.add is None and update.remove is None


def test_a_stored_non_ascii_name_does_not_stop_a_patch_that_repairs_it():
    current = current_contact(name="Jörg", localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    update = with_current(op("replace", "/contactInfo/name/full", value="Joerg"), current=current)

    assert {f.form: f.name for f in update.change.postal_info} == {"int": "Joerg", "loc": "Joerg"}


ORG_CURRENT = dict(
    type=ContactType.ORG, organisationName="ACME Inc.", localizedPostalInfo=localized(name="Yohn", address=ADDRESS),
)


def test_moving_the_organisation_to_the_localization_is_not_undone_by_the_stored_form():
    update = with_current(
        op("remove", "/contactInfo/organizations/org"),
        op("add", "/contactInfo/localizations/und/organizations", value={"org": {"name": "ACME Inc."}}),
        current=current_contact(**ORG_CURRENT),
    )

    forms = {f.form: f for f in update.change.postal_info}
    assert forms["int"].organisationName == "" and forms["loc"].organisationName == "ACME Inc."


def test_a_status_added_without_a_reason_next_to_a_read_operation_keeps_the_stored_reason():
    update = with_current(
        op("replace", "/contactInfo/emails/email/address", value="b@example.example"),
        op("add", "/status", value=STATUS),
        current=current_contact(**STORED),
    )

    assert update.add is None and update.remove is None and update.change.email == "b@example.example"


def test_a_name_patch_leaves_a_hidden_localization_that_differs_from_the_card():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.",
        localizedPostalInfo=localized(name="John Doe", address=ADDRESS),
    )

    update = with_current(op("replace", "/contactInfo/name/full", value="Jane Doe"), current=current)

    assert [f.form for f in update.change.postal_info] == ["int"]


def test_a_name_change_does_not_write_the_organisation_into_the_localization_that_lacks_it():
    update = with_current(op("replace", "/contactInfo/name/full", value="Jane Doe"), current=current_contact(**ORG_CURRENT))

    assert [f.form for f in update.change.postal_info] == ["int"]
