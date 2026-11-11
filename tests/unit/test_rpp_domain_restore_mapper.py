import pytest
from jsonschema import ValidationError

from core.model.domain.domain_restore import DomainRestore
from core.model.domain.domain_restore_process import DomainRestoreProcess
from core.model.domain.restore_report import RestoreReport
from core.capabilities.not_supported_by_backend import NotSupportedByBackend
from rpp_to_model_mapper import PatchNotApplicable, domain_restore_patch, domain_restore_process, domain_restore_report

REPORT = {
    "@type": "restoreReport",
    "preData": "Domain example.example was registered on 2024-01-15 with registrant JD-1234.",
    "postData": "Domain example.example is being restored with the same registration data.",
    "deleteTime": "2025-01-10T12:00:00.0Z",
    "restoreTime": "2025-01-20T15:30:00.0Z",
    "restoreReason": "Domain deleted in error by client operator.",
    "statements": [
        "The information in this report is true to the best of my knowledge.",
        "I have a valid reason for restoring this domain name.",
    ],
}
REPORT_MODEL = RestoreReport(
    preData=REPORT["preData"],
    postData=REPORT["postData"],
    deleteTime="2025-01-10T12:00:00.0Z",
    restoreTime="2025-01-20T15:30:00.0Z",
    restoreReason=REPORT["restoreReason"],
    statements=REPORT["statements"],
)
UPDATE = {"@type": "restoreProcess", "restoreReport": REPORT}


# Create (json §8.1.13)

def test_request_without_report():
    assert domain_restore_process.rpp_to_model("foo.example", {"@type": "restoreProcess"}) == DomainRestore(
        name="foo.example",
    )


def test_inline_report_is_not_supported_by_epp():
    """RFC 3915 restores in two steps, a request and then a report. The maintainer chose not to emulate one step."""
    with pytest.raises(NotSupportedByBackend):
        domain_restore_process.rpp_to_model("foo.example", UPDATE)


@pytest.mark.parametrize("rpp", [
    {},
    {"@type": "renewProcess"},
    {"@type": "restoreProcess", "processId": "x"},
    {"@type": "restoreProcess", "restoreStatus": "restored"},
    {"@type": "restoreProcess", "unknown": 1},
])
def test_invalid_create(rpp):
    with pytest.raises((ValidationError, ValueError)):
        domain_restore_process.rpp_to_model("foo.example", rpp)


# Report (json §8.1.14)

def test_report():
    assert domain_restore_report.rpp_to_model("foo.example", UPDATE) == DomainRestore(
        name="foo.example", report=REPORT_MODEL,
    )


def test_report_with_other():
    rpp = {**UPDATE, "restoreReport": {**REPORT, "other": "Supporting information."}}
    assert domain_restore_report.rpp_to_model("foo.example", rpp).report.other == "Supporting information."


def test_lowercase_t_and_z_are_a_valid_date_time():
    rpp = {**UPDATE, "restoreReport": {**REPORT, "deleteTime": "2025-01-10t12:00:00z"}}
    assert domain_restore_report.rpp_to_model("foo.example", rpp).report.deleteTime == "2025-01-10T12:00:00Z"


@pytest.mark.parametrize("member", ["preData", "postData", "deleteTime", "restoreTime", "restoreReason"])
def test_member_rfc3915_requires_is_a_400(member):
    """RFC 3915 §4.2.5 requires every member but `other`; json §6.2.10 restoreTime in the EPP profile."""
    report = {key: value for key, value in REPORT.items() if key != member}
    with pytest.raises(ValueError):
        domain_restore_report.rpp_to_model("foo.example", {**UPDATE, "restoreReport": report})


def test_one_statement_is_a_400():
    """Json §6.2.10: exactly two statements in the EPP Compatibility Profile."""
    report = {**REPORT, "statements": REPORT["statements"][:1]}
    with pytest.raises(ValueError):
        domain_restore_report.rpp_to_model("foo.example", {**UPDATE, "restoreReport": report})


@pytest.mark.parametrize("member", ["deleteTime", "restoreTime"])
@pytest.mark.parametrize("value", ["not a date", "2025-01-10", "2025-01-10T12:00:00", ""])
def test_date_time_that_is_not_rfc3339_is_a_400(member, value):
    report = {**REPORT, member: value}
    with pytest.raises(ValueError):
        domain_restore_report.rpp_to_model("foo.example", {**UPDATE, "restoreReport": report})


@pytest.mark.parametrize("rpp", [
    {"@type": "restoreProcess"},
    {**UPDATE, "processId": "x"},
    {**UPDATE, "restoreReport": {**REPORT, "statements": []}},
    {**UPDATE, "restoreReport": {**REPORT, "statements": ["a", "b", "c"]}},
    {**UPDATE, "restoreReport": {**REPORT, "unknown": 1}},
    {**UPDATE, "restoreReport": {key: value for key, value in REPORT.items() if key != "@type"}},
])
def test_invalid_report(rpp):
    with pytest.raises((ValidationError, ValueError)):
        domain_restore_report.rpp_to_model("foo.example", rpp)


# Patch

def test_patch_adding_the_report():
    patch = [{"op": "add", "path": "/restoreReport", "value": REPORT}]
    assert domain_restore_patch.rpp_to_model("foo.example", patch) == DomainRestore(
        name="foo.example", report=REPORT_MODEL,
    )


def test_patch_built_member_by_member():
    patch = [{"op": "add", "path": f"/restoreReport/{member}", "value": value}
             for member, value in REPORT.items() if member != "@type"]
    assert domain_restore_patch.rpp_to_model("foo.example", patch).report == REPORT_MODEL


def test_patch_without_a_report_is_a_400():
    with pytest.raises((ValidationError, ValueError)):
        domain_restore_patch.rpp_to_model("foo.example", [])


def test_patch_of_a_read_only_member_is_a_400():
    patch = [{"op": "add", "path": "/restoreReport", "value": REPORT},
             {"op": "add", "path": "/restoreStatus", "value": "restored"}]
    with pytest.raises((ValidationError, ValueError)):
        domain_restore_patch.rpp_to_model("foo.example", patch)


def test_patch_removing_what_is_not_there_is_a_422():
    """EPP has no stored report, so the patch applies to an empty restore process."""
    patch = [{"op": "remove", "path": "/restoreReport"}]
    with pytest.raises((PatchNotApplicable, ValueError)):
        domain_restore_patch.rpp_to_model("foo.example", patch)


# Read (json §8.1.15)

@pytest.mark.parametrize("statuses,status", [
    (["pendingRestore"], "pendingRestore"),
    (["pendingDelete"], "rgpPendingDelete"),
    ([], "restored"),
    (["autoRenewPeriod"], "restored"),
])
def test_process_to_rpp(statuses, status):
    assert domain_restore_process.model_to_rpp(DomainRestoreProcess(rgpStatus=statuses)) == {
        "@type": "restoreProcess", "restoreStatus": status,
    }
