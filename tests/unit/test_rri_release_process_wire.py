"""The Release Process Object over the wire of the app composed for RRI (docs/rri/rri-extension.md): TRANSIT."""
import re

import pytest

from tests.helper.fake_rri_client import error, reply
from tests.unit.test_presets_wire import BASE, rri_client
from tests.unit.test_rri_adapter import NAME
from tests.unit.test_rri_wire import BODY_HEADERS, HEADERS, setup

URL = f"/domainNames/{NAME}/processes/releaseProcesses"


@pytest.mark.parametrize("body, disconnect, applied", [
    ({"@type": "releaseProcess"}, "false", True),
    ({"@type": "releaseProcess", "keepNameservers": True}, "false", True),
    ({"@type": "releaseProcess", "keepNameservers": False}, "true", False),
])
def test_create_sends_transit_with_disconnect_and_echoes_what_applied(body, disconnect, applied):
    client, clients = setup(reply())

    response = client.post(URL, json=body, headers=BODY_HEADERS)

    assert response.status_code == 200, response.text
    assert "Location" not in response.headers
    assert response.json() == {"@type": "releaseProcess", "keepNameservers": applied}
    assert len(clients[0].sent) == 1
    assert re.search(r"<domain:transit[ >]", clients[0].sent[0])
    assert f'disconnect="{disconnect}"' in clients[0].sent[0]


@pytest.mark.parametrize("code, status, rpp", [
    ("63300022003", 403, "02201"),
    ("53000080009", 409, "02304"),
    ("53000080012", 409, "02304"),
    ("63300062009", 404, "02303"),
])
def test_refusals_of_the_registry(code, status, rpp):
    client, _ = setup(error(code, "refused"))

    response = client.post(URL, json={"@type": "releaseProcess"}, headers=BODY_HEADERS)

    assert response.status_code == status and response.headers["RPP-Code"] == rpp


@pytest.mark.parametrize("body", [
    {"@type": "releaseProcess", "keepNameservers": "no"},
    {"@type": "releaseProcess", "other": 1},
    {"@type": "authInfoProcess"},
])
def test_an_invalid_create_is_a_bad_request_and_sends_nothing(body):
    client, clients = setup()

    response = client.post(URL, json=body, headers=BODY_HEADERS)

    assert response.status_code == 400, response.text
    assert all(not c.sent for c in clients)


@pytest.mark.parametrize("method, url", [
    ("GET", URL), ("GET", f"{URL}/latest"), ("GET", f"{URL}/p1"),
    ("DELETE", f"{URL}/latest"), ("DELETE", f"{URL}/p1"),
])
def test_every_operation_but_the_create_is_not_implemented(method, url):
    client, clients = setup()

    response = client.request(method, url, headers=HEADERS)

    assert response.status_code == 501 and response.headers["RPP-Code"] == "02101", response.text
    assert all(not c.sent for c in clients)


def test_a_preset_without_the_extension_refuses_the_path():
    headers = {**BODY_HEADERS, "RPP-Preset": f"preset={BASE};version=1.0"}

    response = rri_client().post(URL, json={"@type": "releaseProcess"}, headers=headers)

    assert response.status_code == 400 and response.headers["RPP-Code"] == "02001", response.text
