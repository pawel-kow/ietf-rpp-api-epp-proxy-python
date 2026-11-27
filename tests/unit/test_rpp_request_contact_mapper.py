"""The request contact object of the rri extension (docs/rri/rri-extension.md): id, provMetadata and uriTemplate."""
import pytest
from jsonschema import ValidationError

from extensions.rri.core.model.request_contact import RequestContact
from core.model.shared.availability import Availability
from extensions.rri.rpp.mapping import (
    request_contact_availability, request_contact_patch, request_contact_replacement, request_contacts,
)

# the tests map without an app, so a validator is built on first use (tests/conftest.py)
pytestmark = pytest.mark.lazy_schemas

ID = "DENIC-1000022-GR"

TEMPLATE = "https://example.com/contact?domain={Alabel}"

OTHER = "mailto:abuse@example.com"

CREATE = {"@type": "requestContact", "id": ID, "uriTemplate": TEMPLATE}

STORED = RequestContact(id=ID, uriTemplate=TEMPLATE, clID="DENIC-1000022", upDate="2026-11-12T00:20:20.000000Z")


def test_a_create_is_the_id_and_the_template():
    assert request_contacts.rpp_to_model(CREATE) == RequestContact(id=ID, uriTemplate=TEMPLATE)


@pytest.mark.parametrize("member", ["name", "contactInfo"])
def test_a_create_with_another_member_is_refused(member):
    with pytest.raises(ValueError, match="Undeclared"):
        request_contacts.rpp_to_model({**CREATE, member: "x"})


def test_a_create_without_a_template_is_refused():
    with pytest.raises(ValidationError, match="uriTemplate"):
        request_contacts.rpp_to_model({"@type": "requestContact", "id": ID})


def test_a_create_of_a_contact_is_refused():
    with pytest.raises(ValidationError):
        request_contacts.rpp_to_model({**CREATE, "@type": "contact"})


def test_a_read_shows_the_template_and_the_metadata():
    assert request_contacts.model_to_rpp(STORED) == {
        "@type": "requestContact", "id": ID, "uriTemplate": TEMPLATE,
        "provMetadata": {"@type": "provMetadata", "spClientId": "DENIC-1000022",
                         "upDate": "2026-11-12T00:20:20.000000Z"},
    }


def test_a_full_update_is_the_template():
    wanted = request_contact_replacement.rpp_to_model(ID, {"@type": "requestContact", "uriTemplate": OTHER})

    assert wanted == RequestContact(id=ID, uriTemplate=OTHER)


@pytest.mark.parametrize("member, value", [("id", ID), ("provMetadata", {"@type": "provMetadata", "spClientId": "X"})])
def test_a_full_update_cannot_send_what_it_cannot_change(member, value):
    with pytest.raises(ValueError, match=member):
        request_contact_replacement.rpp_to_model(ID, {"@type": "requestContact", "uriTemplate": OTHER, member: value})


def test_a_full_update_needs_the_template():
    with pytest.raises(ValidationError, match="uriTemplate"):
        request_contact_replacement.rpp_to_model(ID, {"@type": "requestContact"})


def test_a_patch_replaces_the_template():
    wanted = request_contact_patch.rpp_to_model_with_current(
        ID, [{"op": "replace", "path": "/uriTemplate", "value": OTHER}], STORED)

    assert wanted == RequestContact(id=ID, uriTemplate=OTHER)


def test_a_patch_cannot_remove_the_template():
    with pytest.raises(ValidationError, match="uriTemplate"):
        request_contact_patch.rpp_to_model_with_current(ID, [{"op": "remove", "path": "/uriTemplate"}], STORED)


@pytest.mark.parametrize("path", ["/id", "/provMetadata/upDate", "/name"])
def test_a_patch_changes_only_the_template(path):
    with pytest.raises(ValueError, match=path):
        request_contact_patch.rpp_to_model_with_current(ID, [{"op": "add", "path": path, "value": "x"}], STORED)


def test_availability_is_of_a_request_contact():
    assert request_contact_availability.model_to_rpp(Availability(name=ID, available=False, reason="taken")) == {
        "@type": "requestContactAvailability", "available": False, "reason": "taken"}
