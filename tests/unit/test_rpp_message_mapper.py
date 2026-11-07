import pytest

from tests.helper.captured_log import capture_log

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


def test_missing_creation_date_is_the_request_date_of_a_transfer():
    rpp = messages.model_to_rpp(message(transfer(), creationDate=None))
    assert rpp["creationDate"] == DATE


def test_missing_creation_date_is_the_completion_date_of_a_pending_action():
    event = PendingActionEvent(
        objectType="domainName", objectId="FOO.EXAMPLE", approved=True, clientTransactionId=None,
        serverTransactionId="sv-9", completionDate="2026-11-06T10:00:00.000000Z",
    )
    assert messages.model_to_rpp(message(event, creationDate=None))["creationDate"] == "2026-11-06T10:00:00.000000Z"


def test_missing_creation_date_without_an_event_date_is_the_time_of_the_read():
    rpp = messages.model_to_rpp(message(creationDate=None))
    assert rpp["creationDate"].endswith("Z") and rpp["creationDate"] != DATE
    validate_schema("message.read", rpp)


def test_validation_fallback_names_the_data_and_logs_it_without_content():
    with capture_log() as caplog:
        data = messages.model_to_rpp(message(transfer("weird"), data_name="{urn:x}trnData"))["data"]
    assert "{urn:x}trnData" in data["message"]
    assert "{urn:x}trnData" in caplog.text
    assert "FOO.EXAMPLE" not in caplog.text


def test_a_transfer_without_any_date_still_gives_a_message():
    event = transfer(process=None)
    event.requestDate = None
    rpp = messages.model_to_rpp(message(event, creationDate=None))
    assert rpp["data"]["@type"] == "serviceNoticeMessage"
    assert rpp["creationDate"]
    validate_schema("message.read", rpp)


def test_a_pending_action_without_any_date_still_gives_a_message():
    event = PendingActionEvent(
        objectType="domainName", objectId="FOO.EXAMPLE", approved=True, clientTransactionId=None,
        serverTransactionId="sv-9", completionDate=None,
    )
    rpp = messages.model_to_rpp(message(event, creationDate=None))
    assert rpp["creationDate"]
    validate_schema("message.read", rpp)


def test_the_validation_fallback_cannot_inject_a_log_line(log=None):
    from tests.helper.captured_log import capture_log
    with capture_log() as captured:
        messages.model_to_rpp(message(transfer("weird"), id="4\nFAKE LOG LINE", data_name="{urn:x}trnData"))
    assert captured.lines and all("\n" not in line for line in captured.lines)
