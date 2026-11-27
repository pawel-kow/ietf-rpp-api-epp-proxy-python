"""The request contacts of the RRI adapter: an RRI contact of type REQUEST, which is a handle and a URI template
(docs/rri/rri-5.0-reference.md §5.1, docs/rri/rri-extension.md)."""
from extensions.rri.core.model.request_contact import RequestContact
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from registry_adapter.rri.gateways.rri_backend import RriBackend
from tests.helper.fake_rri_client import FakeRriClient, error, reply
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from tests.helper.profiles import RRI_PARTS, RRI_PROFILE
from tests.unit.test_rri_adapter import CONTACT_INFO

HANDLE = "DENIC-1000022-GR"

TEMPLATE = "https://example.com/contact?domain={Alabel}"

REQUEST_INFO = reply(data=(
    '<contact:infoData xmlns:contact="http://registry.denic.de/contact/5.0">'
    f'<contact:handle>{HANDLE}</contact:handle><contact:type>REQUEST</contact:type>'
    f'<contact:uri-template>{TEMPLATE}</contact:uri-template>'
    '<contact:changed>2026-11-12T01:20:20+01:00</contact:changed></contact:infoData>'))


def backend(*replies):
    client = FakeRriClient(replies=list(replies))
    return RriBackend(client, RRI_PROFILE, extension_parts=RRI_PARTS), client


def test_info_reads_a_request_contact():
    gateway, client = backend(REQUEST_INFO)

    response = gateway.extension(EXTENSION_ID).request_contacts.info(HANDLE)

    assert "<contact:info>" in client.sent[0] and f"<contact:handle>{HANDLE}</contact:handle>" in client.sent[0]
    assert response.payload == RequestContact(id=HANDLE, uriTemplate=TEMPLATE, clID="DENIC-1000022",
                                              upDate="2026-11-12T00:20:20.000000Z")


def test_a_person_or_org_is_no_request_contact():
    gateway, _ = backend(CONTACT_INFO)

    response = gateway.extension(EXTENSION_ID).request_contacts.info("DENIC-1000022-HOLDER")

    assert isinstance(response, ErrorResponse) and response.code == ResultCode.OBJECT_DOES_NOT_EXIST


def test_a_request_contact_is_no_contact():
    gateway, _ = backend(REQUEST_INFO)

    response = gateway.contacts.info(HANDLE)

    assert isinstance(response, ErrorResponse) and response.code == ResultCode.OBJECT_DOES_NOT_EXIST


def test_a_missing_request_contact_is_404():
    gateway, _ = backend(error("53000060009", "At least one contact does not exist"))

    assert gateway.extension(EXTENSION_ID).request_contacts.info(HANDLE).code == ResultCode.OBJECT_DOES_NOT_EXIST


def test_create_sends_the_type_and_the_template():
    gateway, client = backend(reply())

    response = gateway.extension(EXTENSION_ID).request_contacts.create(RequestContact(id=HANDLE, uriTemplate=TEMPLATE), "cl-1")

    assert "<contact:create>" in client.sent[0]
    assert "<contact:type>REQUEST</contact:type>" in client.sent[0]
    assert f"<contact:uri-template>{TEMPLATE}</contact:uri-template>" in client.sent[0]
    assert "<contact:name>" not in client.sent[0] and "<ctid>cl-1</ctid>" in client.sent[0]
    assert response.payload == RequestContact(id=HANDLE)


def test_a_template_rri_refuses_is_a_syntax_error():
    gateway, _ = backend(error("83000000005", "Validation of URI-Template failed"))

    response = gateway.extension(EXTENSION_ID).request_contacts.create(RequestContact(id=HANDLE, uriTemplate="ftp://x.example/"))

    assert response.code == ResultCode.PARAMETER_VALUE_SYNTAX_ERROR and response.registry_code == "83000000005"


def test_replace_sends_the_new_template():
    gateway, client = backend(REQUEST_INFO, reply())

    outcome = gateway.extension(EXTENSION_ID).request_contacts.replace(RequestContact(id=HANDLE, uriTemplate="mailto:abuse@example.com"))

    assert not outcome.unchanged
    assert "<contact:update>" in client.sent[1] and "<contact:type>REQUEST</contact:type>" in client.sent[1]
    assert "<contact:uri-template>mailto:abuse@example.com</contact:uri-template>" in client.sent[1]


def test_replace_with_the_same_template_sends_nothing():
    gateway, client = backend(REQUEST_INFO)

    outcome = gateway.extension(EXTENSION_ID).request_contacts.replace(RequestContact(id=HANDLE, uriTemplate=TEMPLATE))

    assert outcome.unchanged and len(client.sent) == 1


def test_replace_of_a_person_is_404():
    gateway, client = backend(CONTACT_INFO)

    outcome = gateway.extension(EXTENSION_ID).request_contacts.replace(RequestContact(id="DENIC-1000022-HOLDER", uriTemplate=TEMPLATE))

    assert outcome.code == ResultCode.OBJECT_DOES_NOT_EXIST and len(client.sent) == 1


def test_check_shares_the_handles_of_contacts():
    gateway, client = backend(reply(data=(
        '<contact:checkData xmlns:contact="http://registry.denic.de/contact/5.0">'
        f'<contact:handle>{HANDLE}</contact:handle><contact:status>free</contact:status></contact:checkData>')))

    assert gateway.extension(EXTENSION_ID).request_contacts.check(HANDLE).payload.available
    assert "<contact:check>" in client.sent[0]


def test_delete_is_not_a_command_of_rri():
    gateway, client = backend()

    assert gateway.extension(EXTENSION_ID).request_contacts.delete(HANDLE).code == ResultCode.UNIMPLEMENTED_COMMAND and not client.sent
