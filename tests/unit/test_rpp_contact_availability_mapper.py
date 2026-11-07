from models import ContactCheckResponse, ResultCode
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
