import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from models import ContactType
from rpp_to_model_mapper import contact_patch
from tests.helper.contact_fixtures import ADDRESS, current_contact, localized

ID = "JD-1234"
STATUS = {"@type": "contactStatus", "label": "clientUpdateProhibited"}


def op(name, path, **members):
    return {"op": name, "path": path, **members}


def direct(*operations):
    return map_request(contact_patch.rpp_to_model, ID, list(operations))


def with_current(*operations, current=None):
    return map_request(contact_patch.rpp_to_model_with_current, ID, list(operations), current or current_contact())


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
    op("replace", "/contactInfo/emails/email/address", value="b@example.example"),
    op("remove", "/status"),
    op("remove", "/status", match={"label": "clientUpdateProhibited", "reason": "x"}),
    op("replace", "/status", value=[STATUS]),
])
def test_these_need_the_current_contact(operation):
    assert direct(operation) is None


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
