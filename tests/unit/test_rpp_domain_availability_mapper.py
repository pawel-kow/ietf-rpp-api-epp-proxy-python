import pytest

from core.model.domain.domains import DomainCheckResponseSingle
from core.result.result_code import ResultCode
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from rpp.mapping.domain import domain_availability


def availability(available, reason):
    return DomainCheckResponseSingle(
        domain_name="foo.example", available=available, reason=reason, code=ResultCode.COMMAND_COMPLETED_SUCCESSFULLY,
        msg="ok", server_transaction_id="sv", client_transaction_id=None,
    )


def test_taken_domain_gives_the_reason():
    assert domain_availability.model_to_rpp(availability(False, "In use")) == {
        "@type": "domainNameAvailability", "available": False, "reason": "In use",
    }


def test_available_domain_has_no_reason_even_if_the_server_sends_one():
    assert domain_availability.model_to_rpp(availability(True, "In use")) == {
        "@type": "domainNameAvailability", "available": True,
    }


def test_a_check_without_uname_and_lgr_is_accepted():
    domain_availability.rpp_to_model(None, None)


@pytest.mark.parametrize("u_name, lgr", [("bücher.example", None), (None, "latn-1.0"), ("bücher.example", "latn-1.0")])
def test_a_check_with_uname_or_lgr_is_refused(u_name, lgr):
    with pytest.raises(NotSupportedByBackend):
        domain_availability.rpp_to_model(u_name, lgr)
