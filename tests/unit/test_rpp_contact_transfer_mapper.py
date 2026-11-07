import pytest
from jsonschema import ValidationError

from models import AuthInfo, ContactTransfer, ContactTransferProcess, TransferOperation
from rpp_to_model_mapper import NotSupportedByEpp, contact_transfer_approve, contact_transfer_process, contact_transfer_reject

PROCESS = {"@type": "transferProcess"}


def process():
    return ContactTransferProcess(
        id="FO-1",
        trStatus="pending",
        reqClientId="ClientX",
        requestDate="2000-06-08T22:00:00.000000Z",
        actClientId="ClientY",
        actionDate="2000-06-13T22:00:00.000000Z",
    )


def test_request_needs_only_the_type():
    transfer = contact_transfer_process.rpp_to_model("FO-1", PROCESS, None)
    assert transfer == ContactTransfer(id="FO-1", operation=TransferOperation.REQUEST)


def test_request_keeps_the_authorization():
    rpp = {**PROCESS, "transferDir": "pull"}
    transfer = contact_transfer_process.rpp_to_model("FO-1", rpp, "authinfo value=MmZvb0JBUg==")
    assert transfer.authInfo == AuthInfo(pw="2fooBAR")


def test_period_is_not_a_member_of_a_contact_transfer():
    """Json §4.4, RFC 5733 §3.2.4: a contact transfer has no period."""
    rpp = {**PROCESS, "transferPeriod": {"@type": "period", "value": 1, "unit": "y"}}
    with pytest.raises(ValueError):
        contact_transfer_process.rpp_to_model("FO-1", rpp, None)


def test_push_cannot_reach_epp():
    rpp = {**PROCESS, "transferDir": "push", "gainingClientId": "ClientX"}
    with pytest.raises(NotSupportedByEpp):
        contact_transfer_process.rpp_to_model("FO-1", rpp, None)


def test_gaining_client_without_direction_cannot_reach_epp():
    with pytest.raises(NotSupportedByEpp, match="gainingClientId"):
        contact_transfer_process.rpp_to_model("FO-1", {**PROCESS, "gainingClientId": "ClientX"}, None)


def test_request_is_validated():
    with pytest.raises(ValidationError):
        contact_transfer_process.rpp_to_model("FO-1", {"@type": "domainTransferProcess"}, None)


@pytest.mark.parametrize("no_body", [None, {}])
def test_reject_body_is_optional(no_body):
    transfer = contact_transfer_reject.rpp_to_model("FO-1", no_body, None)
    assert transfer == ContactTransfer(id="FO-1", operation=TransferOperation.REJECT)


def test_reject_reason_is_not_allowed_in_the_epp_profile():
    with pytest.raises(NotSupportedByEpp, match="reason"):
        contact_transfer_reject.rpp_to_model("FO-1", {**PROCESS, "reason": "No"}, None)


def test_read_is_the_draft_example():
    """json §8.2.6: no period, no expiry date, no process id."""
    assert contact_transfer_process.model_to_rpp(process()) == {
        "@type": "transferProcess",
        "trStatus": "pending",
        "transferDir": "pull",
        "reqClientId": "ClientX",
        "requestDate": "2000-06-08T22:00:00.000000Z",
        "actClientId": "ClientY",
        "actionDate": "2000-06-13T22:00:00.000000Z",
    }


@pytest.mark.parametrize("member", ["trStatus", "reqClientId", "actClientId", "requestDate", "actionDate", "processId"])
def test_request_with_a_read_only_member_is_rejected(member):
    """Json §4.4."""
    with pytest.raises(ValueError):
        contact_transfer_process.rpp_to_model("FO-1", {**PROCESS, member: "x"}, None)


def test_approve_body_is_optional():
    transfer = contact_transfer_approve.rpp_to_model("FO-1", None, "authinfo value=MmZvb0JBUg==")
    assert transfer == ContactTransfer(id="FO-1", operation=TransferOperation.APPROVE, authInfo=AuthInfo(pw="2fooBAR"))


def test_approve_takes_the_type_only():
    assert contact_transfer_approve.rpp_to_model("FO-1", PROCESS, None).operation == TransferOperation.APPROVE


@pytest.mark.parametrize("body", [{}, [], {"x": 1}, {"@type": "nonsense"}, {**PROCESS, "unknown": 1}])
def test_approve_body_is_validated(body):
    with pytest.raises((ValidationError, ValueError)):
        contact_transfer_approve.rpp_to_model("FO-1", body, None)


def test_approve_reason_is_not_allowed_in_the_epp_profile():
    with pytest.raises(NotSupportedByEpp, match="reason"):
        contact_transfer_approve.rpp_to_model("FO-1", {**PROCESS, "reason": "ok"}, None)
