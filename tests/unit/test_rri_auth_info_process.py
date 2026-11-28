"""The authorisation information processes below the wire: the paths a preset check reads, the RRI commands and gateways."""
from datetime import date

import pytest

from core.model.shared.common import AuthInfo
from core.result.error_response import ErrorResponse
from core.result.result_code import ResultCode
from extensions.rri.core.model.auth_info_setting import AuthInfoSetting
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from registry_adapter.rri.result_codes import result_code
from rpp.http.extension_paths import plural, process_owners, process_segment
from tests.helper.fake_rri_client import error, reply
from tests.unit.test_rri_adapter import DOMAIN_INFO, NAME, _domain, backend
from tests.unit.test_rri_auth_info_process_wire import WITHOUT


@pytest.mark.parametrize("path, segment", [
    ("/domainNames/foo.de/processes/authInfoProcesses", ("domainNames", "authInfoProcesses")),
    ("/domainNames/foo.de/processes/authInfoProcesses/latest", ("domainNames", "authInfoProcesses")),
    ("/contacts/c1/processes/authInfoProcesses", ("contacts", "authInfoProcesses")),
    ("/contacts/c1/processes/transferProcesses/latest/transferApprove", ("contacts", "transferProcesses")),
    ("/domainNames/foo.de", None),
    ("/domainNames/foo.de/processes", None),
    ("/requestContacts/c1", None),
])
def test_the_segment_of_a_process_path(path, segment):
    assert process_segment(path) == segment


def test_the_plural_of_an_identifier_ending_in_s_has_es():
    assert plural("authInfoProcess") == "authInfoProcesses" and plural("requestContact") == "requestContacts"


def test_the_process_owners_are_those_of_the_offered_extensions_only():
    assert process_owners([EXTENSION_ID]) == {("domainNames", "authInfoProcesses"): EXTENSION_ID,
                                              ("domainNames", "authInfoIssueProcesses"): EXTENSION_ID,
                                              ("domainNames", "verificationProcesses"): EXTENSION_ID,
                                              ("domainNames", "releaseProcesses"): EXTENSION_ID}
    assert process_owners([]) == {}


def gateways():
    rri, client = backend(DOMAIN_INFO)
    return rri.extension(EXTENSION_ID), client


def test_info_gives_the_last_day_and_the_sponsor():
    gateway, _ = gateways()

    process = gateway.auth_info_processes.info(NAME).payload

    assert process.expiry_date == date(2026, 11, 13) and process.sponsor_id == "DENIC-1000022"


def test_info_of_a_domain_without_authinfo1_has_no_date():
    rri, _ = backend(WITHOUT)

    assert rri.extension(EXTENSION_ID).auth_info_processes.info(NAME).payload.expiry_date is None


def test_create_sends_no_expire_without_a_date_and_is_not_printed():
    rri, client = backend(reply())

    rri.extension(EXTENSION_ID).auth_info_processes.create(AuthInfoSetting(name=NAME, password="Abc23456"))

    assert "expire=" not in client.sent[0] and client.loggable == [False]


def test_the_hash_of_a_domain_create_is_not_printed_either():
    rri, client = backend(reply(), reply())

    rri.domains.create(_domain(authInfo=AuthInfo(pw="Abc2345678")))

    assert any("createAuthInfo1" in sent for sent in client.sent)
    assert [loggable for sent, loggable in zip(client.sent, client.loggable) if "hash=" in sent] == [False]


@pytest.mark.parametrize("code, result", [
    ("63391068618", ResultCode.PARAMETER_VALUE_RANGE_ERROR),
    ("63391068603", ResultCode.PARAMETER_VALUE_RANGE_ERROR),
    ("63391068704", ResultCode.OBJECT_EXISTS),
])
def test_the_refusals_of_create_authinfo1(code, result):
    rri, _ = backend(error(code, "refused"))

    refused = rri.extension(EXTENSION_ID).auth_info_processes.create(
        AuthInfoSetting(name=NAME, password="Abc23456", expiry_date=date(2026, 12, 1)))

    assert isinstance(refused, ErrorResponse) and refused.code == result and refused.registry_code == code


def test_the_range_refusal_is_command_specific():
    """The same code of another command keeps the general table: the mapping is not global."""
    assert result_code("63391068618") == ResultCode.PARAMETER_VALUE_POLICY_ERROR


def info_with(stated):
    """The INFO of the fixture with another `domain:authInfo1`."""
    rri, _ = backend(DOMAIN_INFO.replace("2026-11-14T00:00:00+01:00", stated))
    return rri.extension(EXTENSION_ID).auth_info_processes.info(NAME).payload


@pytest.mark.parametrize("stated, day", [
    ("2026-11-30T00:00:00+01:00", date(2026, 11, 29)),
    ("2026-11-30T00:00:00.5+01:00", date(2026, 11, 30)),
    ("2026-11-30T00:00:00.000000+01:00", date(2026, 11, 29)),
    ("2026-11-29T24:00:00+01:00", date(2026, 11, 29)),
    ("2026-11-30T23:59:59-05:00", date(2026, 11, 30)),
    ("2026-11-30T00:00:00Z", date(2026, 11, 29)),
    ("2026-11-30T00:00:00", date(2026, 11, 29)),
    ("2026-12-31T24:00:00", date(2026, 12, 31)),
])
def test_the_last_valid_day_is_the_day_before_the_instant_in_the_offset_of_the_registry(stated, day):
    process = info_with(stated)

    assert process.exists and process.expiry_date == day


def test_an_instant_the_proxy_cannot_read_is_an_authinfo1_without_a_date_and_logged_by_its_field(caplog):
    for stated in ("2026-11-30T24:30:00+01:00", "2026-11-30T24:00:00.5+01:00", "2026-13-30T00:00:00+01:00", "nonsense"):
        process = info_with(stated)
        assert process.exists and process.expiry_date is None
    assert "authInfo1" in caplog.text and "nonsense" not in caplog.text
