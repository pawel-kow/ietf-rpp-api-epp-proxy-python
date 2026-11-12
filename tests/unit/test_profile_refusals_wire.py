"""The refusals the profile drives, before any command: transfer operations, restore reports and a readable authInfo."""
import base64
from dataclasses import replace

import pytest

from core.session.session_pool import SessionPool
from registry_adapter.epp.profile import EPP_PROFILE
from rpp.http.app import create_app
from tests.helper.epp_backends import epp_backends
from tests.helper.fake_epp_client import FakeEppClient

MEDIA_TYPE = "application/rpp+json"

HEADERS = {
    "Authorization": "Basic " + base64.b64encode(b"user:pw").decode(),
    "Accept": MEDIA_TYPE,
    "RPP-Cltrid": "cl-1",
}

BODY_HEADERS = {**HEADERS, "Content-Type": MEDIA_TYPE}

REPORT = {
    "@type": "restoreReport",
    "preData": "Before.", "postData": "After.",
    "deleteTime": "2025-01-10T12:00:00.0Z", "restoreTime": "2025-01-20T15:30:00.0Z",
    "restoreReason": "Deleted in error.",
    "statements": ["True to the best of my knowledge.", "A valid reason."],
}


def setup(profile):
    clients = []

    def factory(username, password):
        clients.append(FakeEppClient(username, password, replies=[]))
        return clients[-1]

    return create_app(SessionPool(epp_backends(factory)), profile).test_client(), clients


def assert_refused(response, code, clients):
    assert response.status_code == 501
    assert response.headers["RPP-Code"] == code
    assert all(not client.sent for client in clients)


TRANSFERS = [
    ("domain", "request", "POST", "/domainNames/foo.example/processes/transferProcesses",
     {"@type": "domainTransferProcess", "transferDir": "pull"}),
    ("domain", "query", "GET", "/domainNames/foo.example/processes/transferProcesses/latest", None),
    ("domain", "cancel", "DELETE", "/domainNames/foo.example/processes/transferProcesses/latest", None),
    ("domain", "approve", "POST", "/domainNames/foo.example/processes/transferProcesses/latest/transferApprove", None),
    ("contact", "request", "POST", "/contacts/C1/processes/transferProcesses",
     {"@type": "transferProcess", "transferDir": "pull"}),
    ("contact", "query", "GET", "/contacts/C1/processes/transferProcesses/latest", None),
]


@pytest.mark.parametrize("obj, operation, method, url, body", TRANSFERS)
def test_a_transfer_operation_the_backend_lacks_is_refused_without_a_command(obj, operation, method, url, body):
    profile = replace(EPP_PROFILE, **{f"{obj}_transfer_operations": EPP_PROFILE.domain_transfer_operations - {operation}})
    client, clients = setup(profile)

    response = client.request(method, url, json=body, headers=BODY_HEADERS if body else HEADERS)

    assert_refused(response, "02101", clients)


def test_a_restore_report_is_refused_by_a_backend_without_reports():
    client, clients = setup(replace(EPP_PROFILE, restore_report=False))

    response = client.put("/domainNames/foo.example/processes/restoreProcesses/latest",
                          json={"@type": "restoreProcess", "restoreReport": REPORT}, headers=BODY_HEADERS)

    assert_refused(response, "02102", clients)


def test_include_elements_auth_info_is_refused_where_auth_info_cannot_be_read():
    client, clients = setup(replace(EPP_PROFILE, auth_info_readable=False))

    response = client.get("/domainNames/foo.example?includeElements=authInfo", headers=HEADERS)

    assert_refused(response, "02102", clients)
