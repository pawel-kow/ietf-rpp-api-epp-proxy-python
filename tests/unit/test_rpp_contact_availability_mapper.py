from core.model.shared.availability import Availability
from rpp.mapping.contact import contact_availability


def availability(available, reason=None):
    return Availability(name="JD-1234", available=available, reason=reason)


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
