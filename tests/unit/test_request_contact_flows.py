"""The flows of a request contact: a mutation is read back, and an update that changes nothing sends nothing."""
from dataclasses import replace

from extensions.rri.core.flows.request_contact_flows import (
    create_request_contact, patch_request_contact, replace_request_contact,
)
from extensions.rri.core.model.request_contact import RequestContact
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.gateways.rri_backend import RriBackend
from tests.helper.fake_rri_client import FakeRriClient, error, reply
from tests.helper.profiles import RRI_PARTS, RRI_PROFILE
from tests.unit.test_rri_request_contacts import HANDLE, REQUEST_INFO, TEMPLATE

OTHER = "mailto:abuse@example.com"


def backend(*replies, username="DENIC-1000022-RRI"):
    client = FakeRriClient(username=username, replies=list(replies))
    return RriBackend(client, RRI_PROFILE, extension_parts=RRI_PARTS), client


def test_create_reads_the_request_contact_back():
    rri, client = backend(reply(), REQUEST_INFO)

    result = create_request_contact(rri, RequestContact(id=HANDLE, uriTemplate=TEMPLATE), "cl-1")

    assert result.stored.uriTemplate == TEMPLATE and len(client.sent) == 2


def test_a_refused_create_is_the_refusal():
    rri, _ = backend(error("83000000005", "Validation of URI-Template failed"))

    result = create_request_contact(rri, RequestContact(id=HANDLE, uriTemplate="x"), "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.PARAMETER_VALUE_SYNTAX_ERROR


def test_replace_updates_and_reads_back():
    rri, client = backend(REQUEST_INFO, reply(), REQUEST_INFO)

    result = replace_request_contact(rri, RequestContact(id=HANDLE, uriTemplate=OTHER), "cl-1")

    assert result.stored is not None and "<contact:update>" in client.sent[1] and len(client.sent) == 3


def test_replace_without_a_change_answers_the_read():
    rri, client = backend(REQUEST_INFO)

    result = replace_request_contact(rri, RequestContact(id=HANDLE, uriTemplate=TEMPLATE), "cl-1")

    assert result.stored.uriTemplate == TEMPLATE and len(client.sent) == 1


def test_replace_without_a_change_by_another_regacc_is_refused():
    rri, _ = backend(REQUEST_INFO, username="DENIC-1000023-RRI")

    result = replace_request_contact(rri, RequestContact(id=HANDLE, uriTemplate=TEMPLATE), "cl-1")

    assert isinstance(result, ErrorResponse) and result.code == ResultCode.AUTHORIZATION_ERROR


def test_patch_applies_to_the_read_request_contact():
    rri, client = backend(REQUEST_INFO, reply(), REQUEST_INFO)

    result = patch_request_contact(rri, HANDLE, lambda current: replace(current, uriTemplate=OTHER), "cl-1")

    assert result.stored is not None and f"<contact:uri-template>{OTHER}" in client.sent[1]


def test_patch_of_a_missing_request_contact_is_the_refusal():
    rri, client = backend(error("53000060009", "At least one contact does not exist"))

    result = patch_request_contact(rri, HANDLE, lambda current: current, "cl-1")

    assert result.code == ResultCode.OBJECT_DOES_NOT_EXIST and len(client.sent) == 1
