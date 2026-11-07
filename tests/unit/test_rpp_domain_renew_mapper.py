import pytest
from jsonschema import ValidationError

from models import DomainRenew, DomainRenewProcess
from rpp_to_model_mapper import domain_renew_process

REQUEST = {"@type": "renewProcess"}


def test_type_only():
    assert domain_renew_process.rpp_to_model("foo.example", REQUEST) == DomainRenew(name="foo.example")


def test_period_and_expiry_date():
    rpp = {**REQUEST, "expiryDate": "2005-04-03T22:00:00.0Z", "renewalPeriod": {"@type": "period", "value": 5, "unit": "y"}}
    renew = domain_renew_process.rpp_to_model("foo.example", rpp)
    assert renew == DomainRenew(name="foo.example", curExpDate="2005-04-03", duration="P5Y")


def test_months():
    rpp = {**REQUEST, "renewalPeriod": {"@type": "period", "value": 6, "unit": "m"}}
    assert domain_renew_process.rpp_to_model("foo.example", rpp).duration == "P6M"


@pytest.mark.parametrize("expiry,date", [
    ("2005-04-03T23:30:00Z", "2005-04-03"),
    ("2005-04-03T23:30:00-02:00", "2005-04-04"),
    ("2005-04-04T01:30:00+03:00", "2005-04-03"),
    ("2005-04-03T00:00:00Z", "2005-04-03"),
])
def test_expiry_date_is_the_utc_date(expiry, date):
    renew = domain_renew_process.rpp_to_model("foo.example", {**REQUEST, "expiryDate": expiry})
    assert renew.curExpDate == date


@pytest.mark.parametrize("rpp", [
    {},
    {"@type": "domainName"},
    {**REQUEST, "unknown": 1},
    {**REQUEST, "processId": "x"},
    {**REQUEST, "expiryDate": "2005-04-03"},
    {**REQUEST, "expiryDate": "tomorrow"},
    {**REQUEST, "renewalPeriod": {"@type": "period", "value": 0, "unit": "y"}},
    {**REQUEST, "renewalPeriod": {"@type": "period", "value": 1, "unit": "d"}},
    {**REQUEST, "renewalPeriod": {"@type": "period", "value": 1}},
    {**REQUEST, "renewalPeriod": {"@type": "period", "value": 1, "unit": "y", "extra": 1}},
])
def test_invalid_request(rpp):
    with pytest.raises((ValidationError, ValueError)):
        domain_renew_process.rpp_to_model("foo.example", rpp)


def test_response():
    rpp = domain_renew_process.model_to_rpp(
        DomainRenewProcess(name="FOO.EXAMPLE", expiryDate="2010-04-03T22:00:00.000000Z"))
    assert rpp == {"@type": "renewProcess", "expiryDate": "2010-04-03T22:00:00.000000Z"}


def test_response_without_expiry_is_the_type_only():
    assert domain_renew_process.model_to_rpp(DomainRenewProcess()) == {"@type": "renewProcess"}
