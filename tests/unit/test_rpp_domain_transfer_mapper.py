import pytest
from jsonschema import ValidationError

from core.model.domain.domain_transfer import DomainTransfer
from core.model.shared.common import AuthInfo
from core.model.shared.domain_transfer_process import DomainTransferProcess
from core.model.shared.transfer_operation import TransferOperation
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from rpp.mapping.domain import domain_transfer_approve, domain_transfer_process, domain_transfer_reject

PROCESS = {"@type": "domainTransferProcess"}


def process(**fields):
    return DomainTransferProcess(
        name="FOO.EXAMPLE",
        trStatus="pending",
        reqClientId="ClientX",
        requestDate="2000-06-08T22:00:00.000000Z",
        actClientId="ClientY",
        actionDate="2000-06-13T22:00:00.000000Z",
        **fields,
    )


def test_request_needs_only_the_type():
    transfer = domain_transfer_process.rpp_to_model("foo.example", PROCESS, None)
    assert transfer == DomainTransfer(name="foo.example", operation=TransferOperation.REQUEST)


def test_request_keeps_the_period_and_the_authorization():
    rpp = {**PROCESS, "transferDir": "pull", "transferPeriod": {"@type": "period", "value": 2, "unit": "y"}}
    transfer = domain_transfer_process.rpp_to_model("foo.example", rpp, "authinfo value=MmZvb0JBUg==")
    assert transfer.duration == "P2Y"
    assert transfer.authInfo == AuthInfo(pw="2fooBAR")


def test_push_cannot_reach_epp():
    rpp = {**PROCESS, "transferDir": "push", "gainingClientId": "ClientX"}
    with pytest.raises(NotSupportedByBackend):
        domain_transfer_process.rpp_to_model("foo.example", rpp, None)


def test_gaining_client_without_direction_cannot_reach_epp():
    with pytest.raises(NotSupportedByBackend, match="gainingClientId"):
        domain_transfer_process.rpp_to_model("foo.example", {**PROCESS, "gainingClientId": "ClientX"}, None)


def test_request_is_validated():
    with pytest.raises(ValidationError):
        domain_transfer_process.rpp_to_model("foo.example", {"@type": "transferProcess"}, None)


@pytest.mark.parametrize("no_body", [None, {}])
def test_reject_body_is_optional(no_body):
    transfer = domain_transfer_reject.rpp_to_model("foo.example", no_body, None)
    assert transfer == DomainTransfer(name="foo.example", operation=TransferOperation.REJECT)


def test_reject_reason_is_not_allowed_in_the_epp_profile():
    with pytest.raises(NotSupportedByBackend, match="reason"):
        domain_transfer_reject.rpp_to_model("foo.example", {**PROCESS, "reason": "No"}, None)


def test_read_is_the_draft_example():
    """json §8.1.8"""
    assert domain_transfer_process.model_to_rpp(process(expiryDate="2002-09-08T22:00:00.000000Z")) == {
        "@type": "domainTransferProcess",
        "trStatus": "pending",
        "transferDir": "pull",
        "reqClientId": "ClientX",
        "requestDate": "2000-06-08T22:00:00.000000Z",
        "actClientId": "ClientY",
        "actionDate": "2000-06-13T22:00:00.000000Z",
        "expiryDate": "2002-09-08T22:00:00.000000Z",
    }


def test_read_leaves_out_an_unknown_expiry_date():
    assert "expiryDate" not in domain_transfer_process.model_to_rpp(process())


@pytest.mark.parametrize("member", ["trStatus", "reqClientId", "actClientId", "requestDate", "actionDate", "expiryDate", "processId"])
def test_request_with_a_read_only_member_is_rejected(member):
    """Json §4.4."""
    with pytest.raises(ValueError):
        domain_transfer_process.rpp_to_model("foo.example", {**PROCESS, member: "x"}, None)


def test_approve_body_is_optional():
    transfer = domain_transfer_approve.rpp_to_model("foo.example", None, "authinfo value=MmZvb0JBUg==")
    assert transfer == DomainTransfer(name="foo.example", operation=TransferOperation.APPROVE, authInfo=AuthInfo(pw="2fooBAR"))


def test_approve_takes_the_type_only():
    assert domain_transfer_approve.rpp_to_model("foo.example", PROCESS, None).operation == TransferOperation.APPROVE


@pytest.mark.parametrize("body", [{}, [], {"x": 1}, {"@type": "nonsense"}, {**PROCESS, "unknown": 1}])
def test_approve_body_is_validated(body):
    with pytest.raises((ValidationError, ValueError)):
        domain_transfer_approve.rpp_to_model("foo.example", body, None)


def test_approve_reason_is_not_allowed_in_the_epp_profile():
    with pytest.raises(NotSupportedByBackend, match="reason"):
        domain_transfer_approve.rpp_to_model("foo.example", {**PROCESS, "reason": "ok"}, None)
