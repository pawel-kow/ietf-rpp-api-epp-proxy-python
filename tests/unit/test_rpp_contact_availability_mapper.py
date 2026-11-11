from core.model.contact.contact_check_response import ContactCheckResponse
from core.result.result_code import ResultCode
from rpp_to_model_mapper import contact_availability


def availability(available, reason=None):
    return ContactCheckResponse(
        contact_id="JD-1234", available=available, reason=reason, code=ResultCode.COMMAND_COMPLETED_SUCCESSFULLY,
        msg="ok", server_transaction_id="sv", client_transaction_id=None,
    )


def test_available_contact():
    assert contact_availability.model_to_rpp(availability(True)) == {"@type": "contactAvailability", "available": True}


def test_taken_contact_gives_the_reason():
    assert contact_availability.model_to_rpp(availability(False, "In use")) == {
        "@type": "contactAvailability", "available": False, "reason": "In use",
    }


def test_available_contact_has_no_reason_even_if_the_server_sends_one():
    assert contact_availability.model_to_rpp(availability(True, "In use")) == {
        "@type": "contactAvailability", "available": True,
    }
