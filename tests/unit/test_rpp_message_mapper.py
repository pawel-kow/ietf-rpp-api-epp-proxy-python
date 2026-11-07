import pytest

from models import (
    ContactTransferProcess, DomainTransferProcess, PendingActionEvent, QueueMessage, TransferEvent,
)
from rpp_schema_validator import validate_schema
from rpp_to_model_mapper import messages

DATE = "2026-11-05T16:49:34.000000Z"


def message(event=None, **kwargs):
    values = dict(id="42", creationDate=DATE, lang="en", text="Some text.", event=event)
    return QueueMessage(**{**values, **kwargs})


def domain_process():
    return DomainTransferProcess(
        name="FOO.EXAMPLE", trStatus="pending", reqClientId="baz", requestDate=DATE, actClientId="foo", actionDate=DATE,
    )


def transfer(status="pending", object_type="domainName", process=None):
    return TransferEvent(
        objectType=object_type, objectId="FOO.EXAMPLE", trStatus=status, requestDate=DATE, actionDate=DATE,
        expiryDate=DATE, process=process,
    )


def test_envelope():
    rpp = messages.model_to_rpp(message())
    assert rpp["@type"] == "message"
    assert rpp["id"] == "42"
    assert rpp["creationDate"] == DATE
    assert rpp["status"] == "queued"
    validate_schema("message.read", rpp)


def test_pending_transfer_is_a_transfer_request_message():
    data = messages.model_to_rpp(message(transfer(process=domain_process())))["data"]
    assert data["@type"] == "transferRequestMessage"
    assert data["status"] == "pending"
    assert (data["objectType"], data["objectId"]) == ("domainName", "FOO.EXAMPLE")
    assert data["requestDate"] == DATE and data["actionDate"] == DATE
    assert data["process"]["@type"] == "domainTransferProcess"
    assert "processId" not in data["process"]
    assert "expiryDate" not in data


def test_transfer_without_process():
    assert "process" not in messages.model_to_rpp(message(transfer()))["data"]


@pytest.mark.parametrize("status", ["clientApproved", "clientCancelled", "clientRejected", "serverApproved", "serverCancelled"])
def test_other_status_is_a_transfer_outcome_message(status):
    data = messages.model_to_rpp(message(transfer(status)))["data"]
    assert data["@type"] == "transferOutcomeMessage"
    assert data["trStatus"] == status
    assert data["expiryDate"] == DATE


def test_contact_transfer_carries_a_contact_process():
    process = ContactTransferProcess(
        id="FO-1", trStatus="pending", reqClientId="baz", requestDate=DATE, actClientId="foo", actionDate=DATE,
    )
    data = messages.model_to_rpp(message(transfer(object_type="contact", process=process)))["data"]
    assert data["objectType"] == "contact"
    assert data["process"]["@type"] == "transferProcess"


def test_pending_action_is_a_review_response_message():
    event = PendingActionEvent(
        objectType="domainName", objectId="FOO.EXAMPLE", approved=False, clientTransactionId="cl-9",
        serverTransactionId="sv-9", completionDate=DATE,
    )
    data = messages.model_to_rpp(message(event, text="Denied."))["data"]
    assert data == {
        "@type": "reviewResponseMessage", "objectType": "domainName", "objectId": "FOO.EXAMPLE", "approved": False,
        "clientTransactionId": "cl-9", "serverTransactionId": "sv-9", "completionDate": DATE, "message": "Denied.",
    }


def test_no_event_is_a_service_notice():
    data = messages.model_to_rpp(message())["data"]
    assert data == {"@type": "serviceNoticeMessage", "message": "Some text."}


def test_unmapped_content_is_named_in_the_notice():
    data = messages.model_to_rpp(message(unmapped="urn:example:x other"))["data"]
    assert data["@type"] == "serviceNoticeMessage"
    assert data["message"].startswith("Some text.")
    assert "urn:example:x other" in data["message"]


def test_mapping_that_fails_validation_falls_back_to_a_service_notice():
    rpp = messages.model_to_rpp(message(transfer("weird")))
    assert rpp["data"]["@type"] == "serviceNoticeMessage"
    assert "Some text." in rpp["data"]["message"]
    assert rpp["id"] == "42"
    validate_schema("message.read", rpp)


def test_bad_creation_date_still_gives_a_valid_message():
    rpp = messages.model_to_rpp(message(creationDate="not a date"))
    assert rpp["id"] == "42"
    validate_schema("message.read", rpp)
