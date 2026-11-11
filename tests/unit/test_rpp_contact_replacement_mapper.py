import pytest
from connexion import ProblemException

from controller.helper.rpp_response import map_request
from models import Address, Contact, ContactType
from rpp_to_model_mapper import contact_patch, contact_replacement
from tests.helper.contact_fixtures import ADDRESS, card, current_contact, derived_update, localized, put_body

ID = "JD-1234"


def update(body, current=None, requested=frozenset()):
    return derived_update(current or current_contact(), map_request(contact_replacement.rpp_to_model, ID, body, requested))


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
def test_what_epp_cannot_clear_is_a_501_when_omitted(omitted):
    """A full update is the wanted state, so an omitted member is cleared, and EPP cannot clear these."""
    with pytest.raises(ProblemException) as problem:
        update(put_body(without(card(), omitted)))

    assert problem.value.status == 501 and problem.value.headers["RPP-Code"] == "02102"
    assert "cannot be expressed in EPP" in problem.value.detail


def test_an_omitted_localization_is_a_501():
    current = current_contact(localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    assert rejected(put_body(), current) == 501


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


def test_an_empty_reason_counts_as_none_when_none_is_stored():
    current = current_contact(status=["clientUpdateProhibited"])
    body = put_body(status=[{"@type": "contactStatus", "label": "clientUpdateProhibited", "reason": ""}])

    result = update(body, current)

    assert result.add is None and result.remove is None


def test_an_omitted_status_removes_the_client_statuses():
    result = update(put_body(), current_contact(status=["clientDeleteProhibited"]))

    assert result.remove.status == ["clientDeleteProhibited"] and result.add is None


def test_included_auth_info_is_sent_and_one_not_included_is_left_alone():
    auth = {"@type": "authInfo", "method": "authinfo", "authdata": "NewSecret1!x"}

    assert update(put_body()).change is None
    assert update(put_body(authInfo=auth), requested=frozenset({"authInfo"})).change.authInfo.pw == "NewSecret1!x"


def test_included_auth_info_that_is_stored_changes_nothing():
    auth = {"@type": "authInfo", "method": "authinfo", "authdata": "Secret1!x"}

    assert update(put_body(authInfo=auth), requested=frozenset({"authInfo"})).change is None


def test_included_auth_info_omitted_is_a_501():
    """RFC 5733 has no null element for a contact's authInfo."""
    with pytest.raises(ProblemException) as problem:
        update(put_body(), requested=frozenset({"authInfo"}))

    assert problem.value.status == 501 and problem.value.headers["RPP-Code"] == "02102"


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


B_ADDRESS = {"addr": {"components": [{"kind": "locality", "value": "Bonn"}], "countryCode": "DE"}}
LOC_ONLY = dict(name=None, address=None)


def with_loc(loc_name="Yohn", **members):
    return current_contact(localizedPostalInfo=localized(name=loc_name, address=ADDRESS, **members))


@pytest.mark.parametrize("omitted", ["name", "addresses"])
def test_a_card_member_omitted_next_to_a_localization_is_a_501(omitted):
    body = put_body(without(card(localizations={"und": {"name": {"full": "Yohn"}}}), omitted))

    assert rejected(body, with_loc()) == 501


def test_a_localization_without_a_name_takes_the_name_of_the_card():
    body = put_body(card(localizations={"und": {"addresses": B_ADDRESS}}))

    (form,) = update(body, with_loc()).change.postal_info

    assert (form.form, form.name, form.address) == ("loc", "John Doe", Address(street=None, city="Bonn", country="DE"))


def test_a_repeated_put_with_a_completed_localization_sends_nothing():
    body = put_body(card(localizations={"und": {"addresses": B_ADDRESS}}))
    settled = current_contact(localizedPostalInfo=localized(
        name="John Doe", address=Address(street=None, city="Bonn", country="DE"),
    ))

    assert update(body, settled).change is None


def test_a_localization_the_read_shows_in_part_is_not_rewritten_by_a_repeated_put():
    """The loc has no organisation, the card has one: the read shows only the name, and the PUT inherits the rest."""
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.", localizedPostalInfo=localized(name="Yohn", address=ADDRESS),
    )
    body = put_body(card(
        kind="org", organizations={"org": {"name": "ACME Inc."}}, localizations={"und": {"name": {"full": "Yohn"}}},
    ))

    assert update(body, current).change is None


def test_a_cleared_organisation_is_cleared_in_a_localization_that_shared_it():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.",
        localizedPostalInfo=localized(name="Yohn", organisationName="ACME Inc.", address=ADDRESS),
    )

    body = put_body(card(localizations={"und": {"name": {"full": "Yohn"}}}))

    forms = {f.form: f for f in update(body, current).change.postal_info}

    assert forms["int"].organisationName == "" and forms["loc"].organisationName == ""
    assert forms["loc"].name == "Yohn"


def test_put_and_patch_agree_on_a_cleared_organisation():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.",
        localizedPostalInfo=localized(name="Yohn", organisationName="ACME Inc.", address=ADDRESS),
    )

    patched = derived_update(current, map_request(
        contact_patch.rpp_to_model_with_current, ID, [{"op": "remove", "path": "/contactInfo/organizations/org"}], current,
    ))

    assert patched == update(put_body(card(localizations={"und": {"name": {"full": "Yohn"}}})), current)


def test_a_repeated_localization_of_another_organisation_stays_when_the_card_loses_its_own():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.",
        localizedPostalInfo=localized(name="Yohn", organisationName="ACME GmbH", address=ADDRESS),
    )

    body = put_body(card(kind="org", localizations={"und": {"name": {"full": "Yohn"}, "organizations": {"org": {"name": "ACME GmbH"}}}}))

    forms = {f.form: f for f in update(body, current).change.postal_info}

    assert forms["int"].organisationName == "" and "loc" not in forms


STORED = dict(status=["clientUpdateProhibited"], status_reasons={"clientUpdateProhibited": "why"})
SAME = {"@type": "contactStatus", "label": "clientUpdateProhibited", "reason": "why"}


def test_a_repeated_put_with_a_stored_reason_changes_nothing():
    assert update(put_body(status=[SAME]), current_contact(**STORED)).change is None
    result = update(put_body(status=[SAME]), current_contact(**STORED))
    assert result.add is None and result.remove is None


def test_an_empty_reason_drops_a_stored_reason():
    result = update(put_body(status=[{**SAME, "reason": ""}]), current_contact(**STORED))

    assert result.remove.status == ["clientUpdateProhibited"]
    assert result.add.status == ["clientUpdateProhibited"] and result.add.status_reasons == {}


def test_a_server_status_with_a_stored_text_is_left_alone():
    current = current_contact(status=["ok"], status_reasons={"ok": "all fine"})

    result = update(put_body(), current)

    assert result.add is None and result.remove is None


def test_a_stored_non_ascii_name_does_not_stop_a_put_that_repairs_it():
    current = current_contact(name="Jörg", localizedPostalInfo=localized(name="Jörg", address=ADDRESS))

    forms = {f.form: f for f in update(put_body(), current).change.postal_info}

    assert forms["int"].name == "John Doe" and "loc" in forms


def test_moving_the_organisation_to_the_localization_by_a_put():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.", localizedPostalInfo=localized(name="Yohn", address=ADDRESS),
    )
    body = put_body(card(kind="org", localizations={"und": {"name": {"full": "Yohn"}, "organizations": {"org": {"name": "ACME Inc."}}}}))

    forms = {f.form: f for f in update(body, current).change.postal_info}

    assert forms["int"].organisationName == "" and forms["loc"].organisationName == "ACME Inc."


def test_a_put_changing_the_name_does_not_write_the_organisation_into_the_localization_that_lacks_it():
    current = current_contact(
        type=ContactType.ORG, organisationName="ACME Inc.", localizedPostalInfo=localized(name="Yohn", address=ADDRESS),
    )
    body = put_body(card(
        kind="org", name={"full": "Jane Doe"}, organizations={"org": {"name": "ACME Inc."}},
        localizations={"und": {"name": {"full": "Yohn"}}},
    ))

    assert [f.form for f in update(body, current).change.postal_info] == ["int"]
