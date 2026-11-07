import json

import pytest

from tests.helper.integration_api_test import endpoint_test
from tests.helper.recursive_compare_existing import recusive_compare_existing

REQUEST = {"method": "GET", "url": "/x", "headers": {"RPP-Cltrid": "cl-1"}}
REJECTED = {"status": 422, "body": {"status": 422}, "headers": {"RPP-Code": "02306"}}
CREATED = {"status": 201, "body": {"name": "a"}, "headers": {"RPP-Code": "01000"}}


class FakeResponse:
    def __init__(self, status_code, body, code):
        self.status_code = status_code
        self.text = json.dumps(body)
        self.content = self.text.encode()
        self.headers = {"RPP-Svtrid": "sv-1", "RPP-Code": code, "RPP-Cltrid": "cl-1", "rpp-code": code}


class FakeClient:
    def __init__(self, *responses):
        self.responses = list(responses)

    def request(self, method, url, headers=None, **_):
        return self.responses.pop(0)


def run(client, *responses):
    endpoint_test(client, {"test_id": "t", "steps": [{"request": REQUEST, "response": r} for r in responses]})


@pytest.mark.parametrize("reply", [FakeResponse(422, {"status": 422}, "02306"), FakeResponse(201, {"name": "A"}, "01000")])
def test_any_of_passes_on_either_alternative(reply):
    run(FakeClient(reply), {"any_of": [REJECTED, CREATED]})


def test_any_of_fails_when_no_alternative_matches():
    with pytest.raises(AssertionError, match="No alternative matches"):
        run(FakeClient(FakeResponse(500, {"status": 500}, "02400")), {"any_of": [REJECTED, CREATED]})


def test_any_of_checks_the_headers_of_the_alternative():
    with pytest.raises(AssertionError, match="No alternative matches"):
        run(FakeClient(FakeResponse(201, {"name": "a"}, "01001")), {"any_of": [REJECTED, CREATED]})


def test_any_of_says_why_each_alternative_failed():
    with pytest.raises(AssertionError, match=r"(?s)\[0\].*\[1\]"):
        run(FakeClient(FakeResponse(500, {"status": 500}, "02400")), {"any_of": [REJECTED, CREATED]})


def test_any_of_still_checks_the_headers_of_every_response():
    reply = FakeResponse(201, {"name": "a"}, "01000")
    del reply.headers["RPP-Svtrid"]

    with pytest.raises(AssertionError, match="RPP-Svtrid"):
        run(FakeClient(reply), {"any_of": [CREATED]})


def compare(actual, expected):
    recusive_compare_existing("t", "$", actual, expected)


def test_list_with_a_partial_element_matches_in_any_order():
    key = {"type": "dnskey", "rdata": {"flags": "257"}}
    actual = [{"type": "dnskey", "rdata": {"flags": "257"}}, {"type": "ds", "rdata": {"digest": "AB"}}]

    compare(actual, [{"type": "ds"}, key])
    compare(list(reversed(actual)), [key, {"type": "ds"}])


def test_list_elements_are_used_once():
    with pytest.raises(AssertionError):
        compare([{"a": 1, "b": 2}, {"a": 3}], [{"a": 1}, {"b": 2}])


def test_list_finds_a_pairing_when_a_general_element_comes_first():
    compare([{"a": 1, "b": 2}, {"a": 1}], [{"a": 1}, {"b": 2}])


def test_list_of_another_length_fails():
    with pytest.raises(AssertionError, match=r"\$"):
        compare([1, 2], [1])


def test_list_with_a_different_element_fails():
    with pytest.raises(AssertionError, match=r"\$"):
        compare([1, 2], [1, 3])
