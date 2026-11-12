import json

import pytest

from tests.helper.integration_api_test import (endpoint_test, field_value, replace_pad_placeholders,
                                               replace_upper_placeholders, substitute_captures)
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

    def json(self):
        return json.loads(self.text)


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


CAPTURES = {"expiry": "2027-11-07T07:26:27.000000Z", "leap": "2024-02-29T01:02:03.000000Z", "nothing": None}


def test_capture_is_substituted_everywhere():
    value = {"a": ["x {capture:expiry} y"], "b": {"c": "{capture:expiry}"}, "d": 5}
    assert substitute_captures(value, CAPTURES) == {
        "a": ["x 2027-11-07T07:26:27.000000Z y"], "b": {"c": "2027-11-07T07:26:27.000000Z"}, "d": 5}


def test_capture_plus_years():
    assert substitute_captures("{capture:expiry+2y}", CAPTURES) == "2029-11-07T07:26:27.000000Z"


def test_capture_plus_years_to_29_february_is_not_clamped():
    assert substitute_captures("{capture:leap+4y}", CAPTURES) == "2028-02-29T01:02:03.000000Z"
    with pytest.raises(pytest.fail.Exception, match="29 February|valid"):
        substitute_captures("{capture:leap+1y}", CAPTURES)


@pytest.mark.parametrize("text", [
    "{capture:missing}", "{capture:expiry2}", "{capture:expiry+2m}", "{capture: expiry}", "{capture:}",
    "{capture:expiry+y}", "{capture:nothing}", "{capture:nothing+1y}",
])
def test_bad_capture_fails(text):
    with pytest.raises(pytest.fail.Exception):
        substitute_captures(text, CAPTURES)


def test_field_path_reads_a_list_element_by_index():
    assert field_value([{"id": "41"}, {"id": "42"}], "1.id") == "42"
    assert field_value({"a": [{"b": "c"}]}, "a.0.b") == "c"


@pytest.mark.parametrize("path", ["2.id", "x.id", "-1.id"])
def test_field_path_outside_the_list_fails(path):
    with pytest.raises(AssertionError, match="not found"):
        field_value([{"id": "41"}, {"id": "42"}], path)


def test_capture_from_a_list_body_is_used_by_the_next_step():
    client = FakeClient(FakeResponse(200, [{"id": "42"}], "01301"), FakeResponse(200, {}, "01000"))
    sent = []
    request = client.request
    client.request = lambda method, url, **kw: sent.append(url) or request(method, url, **kw)

    endpoint_test(client, {"test_id": "t", "steps": [
        {"request": REQUEST, "response": {"status": 200, "body": [{}]}, "capture": {"head": "0.id"}},
        {"request": {**REQUEST, "url": "/messages/{capture:head}"}, "response": {"status": 200, "body": {}}},
    ]})

    assert sent == ["/x", "/messages/42"]


def test_upper_placeholder_is_its_text_in_upper_case():
    assert replace_upper_placeholders('"{upper:ns1.t1-ab.net}" and {upper:x}') == '"NS1.T1-AB.NET" and X'


def test_text_without_upper_placeholder_is_unchanged():
    assert replace_upper_placeholders("ns1.{random_name}.net") == "ns1.{random_name}.net"


def test_pad_placeholder_fills_its_text_with_digits_to_the_length():
    assert replace_pad_placeholders("{pad:16:FOO-ab12}.example") == "FOO-ab1201234567.example"


def test_pad_placeholder_repeats_the_digits():
    assert replace_pad_placeholders("{pad:15:t}") == "t01234567890123"


def test_pad_placeholder_of_the_text_length_is_the_text():
    assert replace_pad_placeholders("{pad:3:abc}") == "abc"


def test_pad_placeholder_shorter_than_its_text_fails():
    with pytest.raises(pytest.fail.Exception, match="longer than 2"):
        replace_pad_placeholders("{pad:2:abc}")


def test_delay_seconds_waits_before_the_request():
    waits = []
    client = FakeClient(FakeResponse(201, {"name": "a"}, "01000"), FakeResponse(201, {"name": "a"}, "01000"))
    steps = [{"request": REQUEST, "response": CREATED}, {"delay_seconds": 130, "request": REQUEST, "response": CREATED}]
    endpoint_test(client, {"test_id": "t", "steps": steps}, sleep=lambda seconds: waits.append((seconds, len(client.responses))))
    assert waits == [(130, 1)]


def test_without_delay_seconds_nothing_waits():
    waits = []
    endpoint_test(FakeClient(FakeResponse(201, {"name": "a"}, "01000")),
                  {"test_id": "t", "steps": [{"request": REQUEST, "response": CREATED}]}, sleep=waits.append)
    assert waits == []
