"""The preset check of the process paths of the rri extension: a preset without the extension refuses them, only where the
extension adds them (the collection and the segment), and leaves them out of its OpenAPI document."""
import pytest

from core.session.session_pool import SessionPool
from extensions.rri.core.ports.rri_gateways import EXTENSION_ID
from rpp.http.app import create_app
from rpp.http.extension_paths import process_segment
from rpp.http.preset_middleware import PresetMiddleware
from tests.helper.api_docs import served_client
from tests.helper.profiles import RRI_PROFILE, RRI_REGISTRY
from tests.unit.test_presets_wire import BASE, RRI, rri_client
from tests.unit.test_preset_header_wire import named
from tests.unit.test_openapi_preset_documents import preset_document

PROCESSES = ("authInfoProcesses", "authInfoIssueProcesses", "verificationProcesses", "releaseProcesses")


def named_preset(preset):
    return {**named(preset), "Content-Type": "application/rpp+json"}


@pytest.fixture(scope="module")
def served():
    return served_client(create_app(SessionPool(lambda username, password: None), RRI_PROFILE, registry=RRI_REGISTRY))


def process_paths(document):
    return [path for path in document["paths"] if any(f"/processes/{process}" in path for process in PROCESSES)]


def test_the_base_documents_leave_the_process_paths_out_and_the_rri_document_keeps_them(served):
    base = preset_document(served, BASE)
    rri = preset_document(served, RRI)

    assert process_paths(base) == []
    assert "/domainNames/{name}/processes/renewProcesses" in base["paths"]
    assert {"/domainNames/{name}/processes/authInfoProcesses", "/domainNames/{name}/processes/authInfoProcesses/latest",
            "/domainNames/{name}/processes/authInfoIssueProcesses"} <= set(process_paths(rri))


@pytest.mark.parametrize("preset, status", [(BASE, 404), (RRI, 404)])
@pytest.mark.parametrize("segment", PROCESSES)
def test_a_process_of_another_object_than_the_extension_adds_it_to_is_left_to_routing(preset, status, segment):
    response = rri_client().get(f"/contacts/c1/processes/{segment}", headers=named_preset(preset))

    assert response.status_code == status, response.text


@pytest.mark.parametrize("method, path", [
    ("GET", "/domainNames/x.de/processes/authInfoProcesses/latest"),
    ("DELETE", "/domainNames/x.de/processes/authInfoProcesses/latest"),
    ("POST", "/domainNames/x.de/processes/authInfoIssueProcesses"),
    ("GET", "/domainNames/x.de/processes/verificationProcesses/latest"),
    ("POST", "/domainNames/x.de/processes/releaseProcesses"),
])
def test_a_process_of_the_domain_name_is_refused_under_base_only(method, path):
    refused = rri_client().request(method, path, headers=named_preset(BASE))

    assert refused.status_code == 400 and refused.headers["RPP-Code"] == "02001", refused.text


def test_the_middleware_owns_a_process_segment_for_the_collection_the_extension_adds_it_to_only():
    middleware = PresetMiddleware(None, None, None, [EXTENSION_ID])

    assert middleware.process_owners.get(process_segment("/domainNames/x.de/processes/authInfoProcesses")) == EXTENSION_ID
    assert middleware.process_owners.get(process_segment("/contacts/c1/processes/authInfoProcesses")) is None
    assert middleware.process_owners.get(process_segment("/domainNames/x.de/processes/transferProcesses")) is None
