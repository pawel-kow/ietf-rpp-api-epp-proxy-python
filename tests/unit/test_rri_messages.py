"""The notifications of the registry as RPP messages (docs/rri/rri-extension.md, Mapping to DENIC RRI), over replies built
from the message XSD and the reference's examples (tests/unit/rri_replies/queue_<msgType>.xml): the adapter's typed read, the Query's
`type`, the acknowledgement of a message that is not the oldest, and the app's answers under the presets with and without the extension."""
from pathlib import Path

import pytest

from core.model.message.extension_event import ExtensionEvent
from core.model.message.message_error_response import MessageErrorResponse
from core.model.message.transfer_event import TransferEvent
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from core.session.session_pool import SessionPool
from rpp.http.app import create_app
from rpp.mapping.message.messages import model_to_rpp
from registry_adapter.rri.commands.shared.rri_time import utc_time_of_text
from tests.helper.fake_rri_client import FakeRriClient, error, reply, rri_backends
from tests.helper.profiles import RRI_PROFILE, RRI_REGISTRY
from tests.unit.test_rri_adapter import backend
from tests.unit.test_rri_wire import DISCOVERY, HEADERS

REPLIES = Path(__file__).parent / "rri_replies"

# the RRI msgType of each reply, and the RPP message type it is read as
TYPES = {
    "expireWarning": "domainExpiryWarningMessage", "expire": "domainExpiryMessage",
    "authInfoExpire": "authInfoExpiryMessage", "authInfo2Notify": "authInfoIssueMessage",
    "chprovAuthInfo": "transferOutcomeMessage", "domainDelete": "domainDeletionMessage",
    "authInfo2Delete": "authInfoWithdrawalMessage", "lockCreate": "domainLockMessage",
    "lockDelete": "domainUnlockMessage", "domainUpdate": "domainUpdateMessage", "domainTransit": "domainReleaseMessage",
    "contactUpdate": "contactUpdateMessage", "contactDelete": "contactDeletionMessage",
    "domainStatusUpdate": "domainStatusMessage", "contactVerificationRequired": "contactVerificationMessage",
}

# the extensions that own the types of the registry's lock, changes and deletions (docs/extensions/); the rest is the rri extension's
LOCK = "io.github.pawel-kow.rpp.domain-lock"
CHANGES = "io.github.pawel-kow.rpp.registry-changes"
OWNERS = {"lockCreate": LOCK, "lockDelete": LOCK, "domainUpdate": CHANGES, "contactUpdate": CHANGES,
          "domainDelete": CHANGES, "contactDelete": CHANGES}


def queue(msg_type):
    return reply(data=(REPLIES / f"queue_{msg_type}.xml").read_text())


def message_id(msg_type):
    text = (REPLIES / f"queue_{msg_type}.xml").read_text()
    return text.split('msgid="')[1].split('"')[0]


EMPTY = reply()

PRESET_BASE = "preset=urn:ietf:params:rpp:preset:base;version=1.0"


def setup(*replies):
    clients = []

    def factory(username, password):
        clients.append(FakeRriClient(username, password, replies=list(replies)))
        return clients[-1]

    profile = RRI_PROFILE.with_changes({"presets": ["base", "rri"]})
    app = create_app(SessionPool(rri_backends(factory)), profile, discovery_settings=DISCOVERY, registry=RRI_REGISTRY)
    return app.test_client(), clients


# --- the adapter

@pytest.mark.parametrize("msg_type", TYPES)
def test_every_notification_is_read_as_the_event_of_its_message_type(msg_type):
    gateway, client = backend(queue(msg_type))

    message = gateway.messages.poll().payload.message

    assert "<msg:queue-read" in client.sent[0] and "msgType" not in client.sent[0]
    assert message.id == message_id(msg_type) and message.unmapped is None
    if msg_type == "chprovAuthInfo":
        assert isinstance(message.event, TransferEvent)
        assert (message.event.trStatus, message.event.objectId) == ("serverApproved", "foo.de")
        assert message.event.process.reqClientId == message.event.process.actClientId == "DENIC-1000002"
    else:
        assert isinstance(message.event, ExtensionEvent) and message.event.extension_id == OWNERS.get(msg_type, "de.denic.rpp.rri")


def test_a_query_by_type_reads_each_type_and_the_oldest_wins():
    gateway, client = backend(queue("expire"), queue("lockCreate"), queue("domainUpdate"))
    # the queue reports 3 for each: a type's own count
    response = gateway.messages.poll(message_types=("domainExpiryMessage", "domainLockMessage", "domainUpdateMessage"))

    assert [sent.split('msgType="')[1].split('"')[0] for sent in client.sent] == ["expire", "lockCreate", "domainUpdate"]
    assert response.payload.queue_size == 9
    assert response.payload.message.id == message_id("expire")  # the first of equal msgtimes
    assert response.code == ResultCode.COMMAND_COMPLETED_ACK_TO_DEQUEUE


def test_the_oldest_by_msgtime_wins():
    older = reply(data=(REPLIES / "queue_lockCreate.xml").read_text().replace("2026-11-12T15:51:08+01:00", "2026-11-11T08:00:00+01:00"))
    gateway, _ = backend(queue("expire"), older)

    response = gateway.messages.poll(message_types=("domainExpiryMessage", "domainLockMessage"))

    assert response.payload.message.id == message_id("lockCreate")


def test_a_type_without_a_msgtype_reads_nothing():
    gateway, client = backend()

    response = gateway.messages.poll(message_types=("autoRenewalMessage", "serviceNoticeMessage"))

    assert client.sent == []
    assert response.code == ResultCode.COMMAND_COMPLETED_NO_MESSAGES
    assert response.payload.queue_size == 0 and response.payload.message is None


def test_a_type_without_a_msgtype_is_ignored_next_to_one_with():
    gateway, client = backend(queue("expire"))

    response = gateway.messages.poll(message_types=("autoRenewalMessage", "domainExpiryMessage"))

    assert len(client.sent) == 1 and 'msgType="expire"' in client.sent[0]
    assert response.payload.message.id == message_id("expire")


def test_the_types_of_an_empty_queue_give_an_empty_one():
    gateway, _ = backend(EMPTY, EMPTY)

    response = gateway.messages.poll(message_types=("domainExpiryMessage", "domainLockMessage"))

    assert response.code == ResultCode.COMMAND_COMPLETED_NO_MESSAGES and response.payload.queue_size == 0


def test_the_delete_of_the_oldest_names_no_type():
    gateway, client = backend(reply())

    gateway.messages.ack("a-message-id")

    assert len(client.sent) == 1 and "msgType" not in client.sent[0]


def test_a_message_that_is_not_the_oldest_is_deleted_with_its_type():
    # not the oldest; then the head of each msgType in the order of the XSD up to the one that has the id; the delete
    gateway, client = backend(error("63650063607", "This message is not the oldest"), EMPTY, EMPTY, EMPTY, EMPTY, EMPTY, queue("domainDelete"),
                              reply())

    response = gateway.messages.ack(message_id("domainDelete"))

    assert not isinstance(response, ErrorResponse)
    assert 'msgType="domainDelete"' in client.sent[-1] and f'msgid="{message_id("domainDelete")}"' in client.sent[-1]
    assert len(client.sent) == 8 and all("<msg:delete" not in sent for sent in client.sent[1:-1])


def test_an_id_that_heads_no_type_stays_the_refusal_of_the_registry():
    gateway, client = backend(error("63650063607", "This message is not the oldest"), *[EMPTY] * 15)

    response = gateway.messages.ack("not-a-head-of-any-type")

    assert isinstance(response, ErrorResponse) and response.registry_code == "63650063607"
    assert response.code == ResultCode.OBJECT_DOES_NOT_EXIST and len(client.sent) == 16


def test_another_refusal_of_the_delete_is_not_searched_for():
    gateway, client = backend(error("63650063609", "MsgId does not exist"))

    response = gateway.messages.ack("x-message-id")

    assert isinstance(response, ErrorResponse) and len(client.sent) == 1


def test_a_message_is_found_by_the_type_it_heads():
    gateway, client = backend(*[EMPTY] * 8, queue("lockDelete"))

    response = gateway.messages.find(message_id("lockDelete"))

    assert response.payload.message.id == message_id("lockDelete")
    assert isinstance(response.payload.message.event, ExtensionEvent)
    assert len(client.sent) == 9


def test_no_type_has_the_id():
    gateway, _ = backend(*[EMPTY] * 15)

    response = gateway.messages.find("nobody")

    assert isinstance(response, MessageErrorResponse) and response.code == ResultCode.OBJECT_DOES_NOT_EXIST


def test_a_notice_message_without_notices_has_an_event_with_none():
    gateway, _ = backend(reply(data=(REPLIES / "queue_domainDelete.xml").read_text().replace(
        '<msg:message level="info" code="16350000031"><tr:text>Domain has been deleted</tr:text>'
        '<tr:argument>request-reference DENIC#:4711</tr:argument></msg:message>', "")))

    event = gateway.messages.poll().payload.message.event

    assert isinstance(event, ExtensionEvent) and event.event.notices == ()


def test_a_message_older_by_a_time_without_offset_is_compared_in_utc():
    naive = reply(data=(REPLIES / "queue_lockCreate.xml").read_text().replace("2026-11-12T15:51:08+01:00", "2026-11-12T14:00:00"))
    gateway, _ = backend(queue("expire"), naive)   # 14:51:08 UTC against 14:00:00 UTC

    response = gateway.messages.poll(message_types=("domainExpiryMessage", "domainLockMessage"))

    assert response.payload.message.id == message_id("lockCreate")


def test_the_read_that_fails_after_a_not_the_oldest_answers_its_error():
    gateway, client = backend(error("63650063607", "This message is not the oldest"), error("76000000002", "Timeout while processing request"))

    response = gateway.messages.ack("x-message-id")

    assert isinstance(response, ErrorResponse) and response.registry_code == "76000000002" and len(client.sent) == 2


# --- the app

def data_of(response):
    return response.json()[0]["data"]


@pytest.mark.parametrize("msg_type", TYPES)
def test_a_message_is_of_its_message_type_under_the_rri_preset(msg_type):
    client, _ = setup(queue(msg_type))

    response = client.get("/messages", headers=HEADERS)

    assert response.status_code == 200, response.text
    assert data_of(response)["@type"] == TYPES[msg_type]
    assert response.headers["RPP-Queue-Size"] == "3" and response.headers["RPP-Code"] == "01301"


def test_the_registry_notices_are_the_data_of_the_message():
    client, _ = setup(queue("domainStatusUpdate"))

    data = data_of(client.get("/messages", headers=HEADERS))

    assert data["status"] == [{"@type": "domainStatus", "label": "serverHold"}]
    assert data["holders"] == [{"@type": "objectReference", "objectType": "contact", "objectId": "DENIC-1000022-HOLDER"}]
    assert data["notices"][0]["code"] == "16350000041" and data["notices"][0]["arguments"][1] == "VerificationClaims: address;name"
    assert "level" not in data["notices"][0] and "holdDeadline" not in data


def test_a_bulk_message_lists_its_objects_and_has_no_object_of_its_own():
    client, _ = setup(queue("expireWarning"))

    data = data_of(client.get("/messages", headers=HEADERS))

    assert "objectType" not in data and [o["objectId"] for o in data["objects"]] == ["foo.de", "bar.de"]
    assert all(o["@type"] == "datedObjectReference" and o["date"].endswith("Z") for o in data["objects"])


def test_the_losing_client_reads_a_transfer_outcome_under_every_preset():
    client, _ = setup(queue("chprovAuthInfo"))

    response = client.get("/messages", headers={**HEADERS, "RPP-Preset": PRESET_BASE})

    assert data_of(response)["@type"] == "transferOutcomeMessage" and data_of(response)["trStatus"] == "serverApproved"


def test_a_message_of_the_extension_is_a_service_notice_under_the_preset_without_it():
    client, _ = setup(queue("lockCreate"))

    response = client.get("/messages", headers={**HEADERS, "RPP-Preset": PRESET_BASE})

    assert response.status_code == 200, response.text
    assert data_of(response)["@type"] == "serviceNoticeMessage" and "foo.de" in data_of(response)["message"]
    assert response.json()[0]["id"] == message_id("lockCreate")


@pytest.mark.parametrize("query", ["type=domainLockMessage", "type=domainLockMessage&type=domainExpiryMessage",
                                   "type=domainExpiryMessage,domainLockMessage"])
def test_the_repeated_and_the_comma_separated_type_are_read_alike(query):
    types = query.count("Message")
    client, clients = setup(*[queue("lockCreate")] * types)

    response = client.get(f"/messages?{query}", headers=HEADERS)

    assert response.status_code == 200, response.text
    assert data_of(response)["@type"] == "domainLockMessage"
    assert len(clients[0].sent) == types and all("msgType=" in sent for sent in clients[0].sent)
    assert response.headers["RPP-Queue-Size"] == str(3 * types)   # the sum of the counts of the reads


def test_a_type_without_a_msgtype_answers_an_empty_queue_and_sends_nothing():
    client, clients = setup()

    response = client.get("/messages?type=serviceNoticeMessage", headers=HEADERS)

    assert response.status_code == 200 and response.json() == []
    assert response.headers["RPP-Code"] == "01300" and response.headers["RPP-Queue-Size"] == "0"
    assert clients[0].sent == []


def test_a_message_that_is_not_the_head_is_read_by_its_id():
    own = reply(data=(REPLIES / "queue_lockDelete.xml").read_text().replace('msgcnt="3"', 'msgcnt="1"'))
    client, _ = setup(queue("expire"), *[EMPTY] * 8, own)   # the head's queue holds 3, the type 1

    response = client.get(f"/messages/{message_id('lockDelete')}", headers=HEADERS)

    assert response.status_code == 200, response.text
    assert response.json()["data"]["@type"] == "domainUnlockMessage"
    assert response.headers["RPP-Queue-Size"] == "3"


def test_an_id_that_heads_no_type_is_not_found():
    client, _ = setup(queue("expire"), *[EMPTY] * 15)

    response = client.get("/messages/nobody-has-this-id", headers=HEADERS)

    assert response.status_code == 404 and response.headers["RPP-Code"] == "02303"


def test_a_message_that_is_not_the_oldest_is_acknowledged():
    client, clients = setup(error("63650063607", "This message is not the oldest"), *[EMPTY] * 8, queue("lockDelete"), reply())

    response = client.delete(f"/messages/{message_id('lockDelete')}", headers=HEADERS)

    assert response.status_code == 200, response.text
    assert 'msgType="lockDelete"' in clients[0].sent[-1]


def test_an_event_that_fails_its_definition_is_a_service_notice():
    no_notices = (REPLIES / "queue_domainDelete.xml").read_text().replace(
        '<msg:message level="info" code="16350000031"><tr:text>Domain has been deleted</tr:text>'
        '<tr:argument>request-reference DENIC#:4711</tr:argument></msg:message>', "")
    client, _ = setup(reply(data=no_notices))

    response = client.get("/messages", headers=HEADERS)

    assert response.status_code == 200, response.text
    assert data_of(response)["@type"] == "serviceNoticeMessage" and "foo.de" in data_of(response)["message"]
    assert response.json()[0]["id"] == message_id("domainDelete")


def test_a_query_of_a_type_the_data_of_which_fails_its_definition_answers_the_notice():
    """A documented deviation: the message is read as the type asked for, and is a service notice, as without a type."""
    no_notices = (REPLIES / "queue_domainDelete.xml").read_text().replace(
        '<msg:message level="info" code="16350000031"><tr:text>Domain has been deleted</tr:text>'
        '<tr:argument>request-reference DENIC#:4711</tr:argument></msg:message>', "")
    client, clients = setup(reply(data=no_notices))

    response = client.get("/messages?type=domainDeletionMessage", headers=HEADERS)

    assert response.status_code == 200 and data_of(response)["@type"] == "serviceNoticeMessage"
    assert 'msgType="domainDelete"' in clients[0].sent[0]


def test_a_type_of_the_extension_under_a_preset_without_it_answers_an_empty_queue_and_sends_nothing():
    client, clients = setup()

    response = client.get("/messages?type=domainLockMessage", headers={**HEADERS, "RPP-Preset": PRESET_BASE})

    assert response.status_code == 200 and response.json() == []
    assert response.headers["RPP-Code"] == "01300" and response.headers["RPP-Queue-Size"] == "0"
    assert clients[0].sent == []


def test_a_type_of_the_base_under_a_preset_without_the_extension_is_still_read():
    client, clients = setup(queue("chprovAuthInfo"))

    response = client.get("/messages?type=domainLockMessage,transferOutcomeMessage", headers={**HEADERS, "RPP-Preset": PRESET_BASE})

    assert data_of(response)["@type"] == "transferOutcomeMessage"
    assert len(clients[0].sent) == 1 and 'msgType="chprovAuthInfo"' in clients[0].sent[0]


def test_a_date_as_text_is_in_utc_and_one_without_offset_is_utc():
    assert utc_time_of_text("2026-11-12T15:51:08+01:00") == "2026-11-12T14:51:08.000000Z"
    assert utc_time_of_text("2026-11-12T15:51:08") == "2026-11-12T15:51:08.000000Z"


def test_a_notification_of_an_extension_the_response_preset_lacks_is_a_service_notice():
    gateway, _ = backend(queue("lockCreate"))
    message = gateway.messages.poll().payload.message
    messages_only = ("de.denic.rpp.rri", "io.github.pawel-kow.rpp.messages")

    rpp = model_to_rpp(message, backend_name="RRI", extensions=messages_only)

    assert rpp["data"]["@type"] == "serviceNoticeMessage"
    assert model_to_rpp(message, backend_name="RRI", extensions=(*messages_only, LOCK))["data"]["@type"] == "domainLockMessage"
