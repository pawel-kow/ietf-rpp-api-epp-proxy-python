"""CORS: a browser client of another origin reads the RPP response headers only when the proxy exposes them."""
from tests.helper.integration_api_test import header_list
from tests.unit.test_domain_renew_wire import HEADERS, error_reply, info_reply, setup

ORIGIN = {"Origin": "https://client.example"}


def test_a_response_to_another_origin_exposes_the_rpp_headers_it_carries():
    http, _ = setup(info_reply())

    response = http.get("/domainNames/foo.example", headers={**HEADERS, **ORIGIN})

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ORIGIN["Origin"]
    exposed = header_list(response.headers["Access-Control-Expose-Headers"])
    for name in ("rpp-cltrid", "rpp-svtrid", "rpp-code"):
        assert name in response.headers and name in exposed
    assert {"rpp-queue-size", "rpp-preset", "location"} <= exposed


def test_a_problem_detail_to_another_origin_exposes_the_rpp_headers():
    http, _ = setup(error_reply(2303))

    response = http.get("/domainNames/foo.example", headers={**HEADERS, **ORIGIN})

    assert response.status_code == 404
    assert "rpp-code" in header_list(response.headers["Access-Control-Expose-Headers"])
