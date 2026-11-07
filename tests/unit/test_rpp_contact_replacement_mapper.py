import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from models import Address, Contact, ContactType
from rpp_to_model_mapper import contact_replacement
from tests.helper.contact_fixtures import ADDRESS, card, current_contact, localized, put_body

ID = "JD-1234"


def update(body, current=None):
    checked = map_request(contact_replacement.rpp_to_model, ID, body)
    return map_request(contact_replacement.rpp_to_model_with_current, ID, checked, current or current_contact())


def rejected(body, current=None) -> int:
    with pytest.raises(ProblemException) as problem:
        update(body, current)
    return problem.value.status


def without(contact_info: dict, *members) -> dict:
    return {key: value for key, value in contact_info.items() if key not in members}


def test_a_repeated_contact_changes_nothing():
    result = update(put_body())

    assert result.add is None and result.remove is None and result.change is None


def test_a_new_email_is_sent_alone():
    result = update(put_body(card(emails={"email": {"address": "b@example.example"}})))

    assert result.change.email == "b@example.example"
    assert result.change.postal_info == [] and result.change.voice is None


def test_a_new_number_is_sent_with_its_extension():
    result = update(put_body(card(phones={"voice": {"number": "tel:+49.999"}, "fax": card()["phones"]["fax"]})))

    assert result.change.voice == "+49.999"


def test_omitted_voice_and_fax_are_cleared():
    result = update(put_body(without(card(), "phones")))

    assert (result.change.voice, result.change.fax) == ("", "")


def test_omitted_numbers_that_are_not_set_send_nothing():
    result = update(put_body(without(card(), "phones")), current_contact(phone=None, fax=None))

    assert result.change is None


def test_an_omitted_organisation_is_cleared_in_a_complete_form():
    current = current_contact(type=ContactType.ORG, organisationName="ACME Inc.")

    result = update(put_body(), current)

    (form,) = result.change.postal_info
    assert (form.form, form.name, form.organisationName, form.address) == ("int", "John Doe", "", ADDRESS)


def test_a_new_organisation_is_sent_in_a_complete_form():
    body = put_body(card(kind="org", organizations={"org": {"name": "ACME Inc."}}))

    (form,) = update(body).change.postal_info

    assert (form.name, form.organisationName, form.address) == ("John Doe", "ACME Inc.", ADDRESS)


def test_a_sent_address_replaces_the_whole_address():
    new = {"addr": {"components": [{"kind": "locality", "value": "Bonn"}], "countryCode": "DE"}}

    (form,) = update(put_body(card(addresses=new))).change.postal_info

    assert form.address == Address(street=None, city="Bonn", country="DE")
    assert form.name == "John Doe"


@pytest.mark.parametrize("omitted", ["name", "addresses", "emails"])
def test_what_epp_cannot_clear_is_kept_when_omitted(omitted):
    result = update(put_body(without(card(), omitted)))

    assert result.change is None


def test_an_omitted_localization_is_kept():
    current = current_contact(localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    assert update(put_body(), current).change is None


def test_a_localization_is_sent_complete_with_what_it_leaves_out_from_the_card():
    body = put_body(card(localizations={"de": {"name": {"full": "Jörg"}}}))

    forms = update(body).change.postal_info

    assert [(f.form, f.name, f.address) for f in forms] == [("loc", "Jörg", ADDRESS)]


def test_a_repeated_localization_changes_nothing():
    current = current_contact(localizedPostalInfo=localized(name="Jörg", address=ADDRESS))
    body = put_body(card(localizations={"und": {"name": {"full": "Jörg"}}}))

    assert update(body, current).change is None


def test_an_invisible_localization_follows_a_changed_card():
    """A localization equal to the card reads back as none, so it has to stay equal."""
    current = current_contact(localizedPostalInfo=localized(name="John Doe", address=ADDRESS))
    body = put_body(card(name={"full": "Joe Doe"}))

    forms = {f.form: f for f in update(body, current).change.postal_info}

    assert forms["int"].name == "Joe Doe" and forms["loc"].name == "Joe Doe"


def test_client_statuses_are_a_set():
    current = current_contact(status=["clientDeleteProhibited", "serverUpdateProhibited"])
    body = put_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited", "reason": "why"}])

    result = update(body, current)

    assert result.add.status == ["clientUpdateProhibited"] and result.add.status_reasons == {"clientUpdateProhibited": "why"}
    assert result.remove.status == ["clientDeleteProhibited"]


def test_a_changed_reason_is_a_remove_and_an_add():
    current = current_contact(status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "old"})
    body = put_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited", "reason": "new"}])

    result = update(body, current)

    assert result.remove.status == ["clientUpdateProhibited"]
    assert result.add.status_reasons == {"clientUpdateProhibited": "new"}


def test_an_empty_reason_counts_as_none():
    current = current_contact(status=["clientUpdateProhibited"])
    body = put_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited", "reason": ""}])

    result = update(body, current)

    assert result.add is None and result.remove is None


def test_an_omitted_status_removes_the_client_statuses():
    result = update(put_body(), current_contact(status=["clientDeleteProhibited"]))

    assert result.remove.status == ["clientDeleteProhibited"] and result.add is None


def test_auth_info_present_is_sent_and_omitted_is_left_alone():
    auth = {"@type": "authInfo", "method": "authinfo", "authdata": "Secret1!x"}

    assert update(put_body()).change is None
    assert update(put_body(authInfo=auth)).change.authInfo.pw == "Secret1!x"


@pytest.mark.parametrize("member", ["id", "provMetadata", "processes", "unknown"])
def test_a_member_outside_the_update_schema_is_a_400(member):
    assert rejected({**put_body(), member: {"@type": "x"}}) == 400


@pytest.mark.parametrize("body", [
    put_body(card(foo=1)),
    put_body(card(name={"full": "John Doe", "foo": 1})),
    put_body(card(emails={"email": {"address": "a@example.example", "foo": 1}})),
    put_body(authInfo={"@type": "authInfo", "method": "authinfo", "authdata": "x", "foo": 1}),
    put_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited", "foo": 1}]),
])
def test_an_undeclared_nested_member_is_a_400(body):
    assert rejected(body) == 400


def test_a_server_status_is_a_400():
    assert rejected(put_body(status=[{"@type": "contactStatus", "label": "serverUpdateProhibited"}])) == 400


def test_a_due_date_is_a_501():
    status = {"@type": "contactStatus", "label": "clientUpdateProhibited", "due": "2030-01-01T00:00:00Z"}

    assert rejected(put_body(status=[status])) == 501


def test_disclose_is_a_501():
    assert rejected(put_body(disclose={"@type": "disclose"})) == 501


def test_what_create_refuses_is_refused():
    assert rejected(put_body(card(links={"url": {"uri": "https://example.example"}}))) == 501
    assert rejected(put_body(card(organizations={"org": {"name": "ACME"}}))) == 501


def test_kind_org_without_an_organisation_is_a_400():
    assert rejected(put_body(card(kind="org"))) == 400
