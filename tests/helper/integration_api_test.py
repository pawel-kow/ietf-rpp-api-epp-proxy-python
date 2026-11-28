from .recursive_compare_existing import recusive_compare_existing
import json
import re
import pytest
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from tests.helper.check_datetime import check_datetime_format_utc_and_delta

def header_list(value):
    """The elements of a header that is a list (RFC 9110 §5.6.1, for example Vary), trimmed and in lower case."""
    return {element.strip().lower() for element in value.split(",") if element.strip()}

def evaluate_condition(value, spec):
    if spec["type"] == "not_null":
        return value is not None
    elif spec["type"] == "not_empty_string":
        return isinstance(value, str) and value != ""
    elif spec["type"] == "list_contains":
        # A header that is a list (RFC 9110 §5.6.1, for example Vary): every value of the condition is an element, whatever
        # else the list holds and in whatever order; the elements compare without regard to case.
        elements = header_list(value) if isinstance(value, str) else set()
        return all(wanted.lower() in elements for wanted in spec["values"])
    elif spec["type"] == "datetime_format_utc_and_delta":
        return check_datetime_format_utc_and_delta(
            datetime.fromisoformat(spec["reference"].replace("Z", "+00:00")), value, spec["min_delta"], spec["max_delta"]
        )
    else:
        return False

def field_value(document, path):
    """Reads a dotted field path, for example 'provMetadata.crDate'. A number picks a list element, as in '0.id'."""
    value = document
    for part in path.split("."):
        if isinstance(value, list):
            assert part.isdigit() and int(part) < len(value), f"Field '{path}' not found"
            value = value[int(part)]
        else:
            assert part in value, f"Field '{path}' not found"
            value = value[part]
    return value

def assert_rpp_headers(request_headers, response, test_name):
    """Core §6.2: the headers every response carries."""
    assert response.headers.get("RPP-Svtrid"), f"RPP-Svtrid missing for test case: {test_name}"
    assert re.fullmatch(r"[01]\d{4}", response.headers.get("RPP-Code", "")), f"Malformed RPP-Code for test case: {test_name}"
    if "RPP-Cltrid" in request_headers:
        assert response.headers.get("RPP-Cltrid") == request_headers["RPP-Cltrid"], f"RPP-Cltrid not echoed for test case: {test_name}"

def assert_headers(expected_headers, response, test_name):
    for header, test in expected_headers.items():
        header = header.lower()
        if test is None:
            assert header not in response.headers, f"Header '{header}' should not be present in response for test case: {test_name}"
            continue
        assert header in response.headers, f"Header '{header}' not found in response for test case: {test_name}"
        if isinstance(test, str):
            assert response.headers[header] == test, f"Header '{header}' is {response.headers[header]!r}, not {test!r}, for test case: {test_name}"
        elif isinstance(test, dict) and "type" in test:
            assert evaluate_condition(response.headers[header], test), f"Header '{header}' does not meet the condition {test['type']} for test case: {test_name}"
        else:
            raise ValueError(f"Header '{header}' has unexpected type or value for test case: {test_name}")

def assert_response(expected, response, test_name, signalling="header"):
    # 1. Check the HTTP status code
    if isinstance(expected["status"], list):
        # Check if the response status code is in the list of expected status codes
        assert response.status_code in expected["status"], f"Unexpected status code for test case: {test_name}"
    else:
        assert response.status_code == expected["status"]

    if "content_type" in expected:
        # Check the Content-Type header
        # With the media type signalling (core, Media Type Signalling) the preset is in the parameters: an expected type without
        # parameters is then the media type of the response, whatever its parameters. Otherwise, and for an expected
        # type with parameters, the whole value is compared.
        actual = response.headers["Content-Type"].lower()
        if signalling == "media-type" and ";" not in expected["content_type"]:
            actual = actual.partition(";")[0].strip()
        assert actual == expected["content_type"].lower(), f"Content-Type mismatch for test case: {test_name}"

    # 2. Check the response body (if one is expected)
    if "body" in expected:
        # For JSON responses, compare the parsed JSON
        try:
            response_json = json.loads(response.text)
        except json.JSONDecodeError:
            # If JSON decoding fails, log the response text for debugging
            assert False, f"Failed to decode JSON for test case: {test_name} Response Text: {response.text}"
        assert response_json is not None, f"Response body was not valid JSON for test case: {test_name}"
        # Check if the response JSON matches the expected structure
        recusive_compare_existing(test_name, "$", response_json, expected["body"], case_sensitive=False)
        # Check for expected fields in the response
        # Ensure that the expected fields are present and not null
        for field, test in expected.get("fields", {}).items():
            assert evaluate_condition(field_value(response_json, field), test), f"Field '{field}' does not meet the condition {test['type']} for test case: {test_name}"
    else:
        # For responses expected to have no body (like 100, 204)
        assert not response.content, "Response data not expected" # Check if data attribute is empty

    assert_headers(expected.get("headers", {}), response, test_name)

def assert_any_response(alternatives, response, test_name, signalling="header"):
    """Passes when one alternative matches, for behaviour the protocol leaves to the server."""
    failures = []
    for i, expected in enumerate(alternatives):
        try:
            assert_response(expected, response, test_name, signalling)
            return
        except AssertionError as failure:
            failures.append(f"[{i}] {failure}")
    assert False, "No alternative matches:\n" + "\n".join(failures)

CAPTURE = re.compile(r"\{capture:[^}]*\}")
CAPTURE_FORM = re.compile(r"\{capture:([A-Za-z_]+)(?:\+([0-9]+)y)?\}")

def substitute_captures(value, captures):
    """Replaces {capture:name} with a value an earlier step captured, and {capture:name+Ny} with that
    timestamp N years later. Anything else that looks like a capture fails the test."""
    if isinstance(value, dict):
        return {k: substitute_captures(v, captures) for k, v in value.items()}
    if isinstance(value, list):
        return [substitute_captures(v, captures) for v in value]
    if isinstance(value, str):
        def replace(match):
            form = CAPTURE_FORM.fullmatch(match.group(0))
            if form is None:
                pytest.fail(f"Malformed capture {match.group(0)}, expected {{capture:name}} or {{capture:name+Ny}}")
            name, years = form.groups()
            if not isinstance(captures.get(name), str):
                pytest.fail(f"Capture '{name}' of {match.group(0)} is not a string captured by an earlier step")
            if years is None:
                return captures[name]
            later = datetime.fromisoformat(captures[name].replace("Z", "+00:00"))
            try:
                return later.replace(year=later.year + int(years)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
            except ValueError:
                pytest.fail(f"{match.group(0)}: {years} years after {captures[name]} is not a valid date")
        return CAPTURE.sub(replace, value)
    return value

UPPER = re.compile(r"\{upper:([^{}]*)\}")
LOWER = re.compile(r"\{lower:([^{}]*)\}")

def replace_upper_placeholders(value: str) -> str:
    """Replaces {upper:TEXT} by TEXT in upper case, the form the registry stores a name in, for an exact `match`."""
    """`{lower:TEXT}` is TEXT in lower case, for an id the client sends in another case than the registry stores."""
    value = UPPER.sub(lambda match: match.group(1).upper(), value)
    return LOWER.sub(lambda match: match.group(1).lower(), value)

PAD = re.compile(r"\{pad:(\d+):([^{}]*)\}")
DIGITS = "0123456789"

def replace_pad_placeholders(value: str) -> str:
    """Replaces {pad:N:TEXT} by TEXT followed by the digits 0 to 9, repeated, to N characters: a name or id of an exact
    length that keeps the random part of TEXT. TEXT longer than N fails the test."""
    def replace(match):
        length, text = int(match.group(1)), match.group(2)
        if len(text) > length:
            pytest.fail(f"{match.group(0)}: the text is longer than {length} characters")
        missing = length - len(text)
        return text + (DIGITS * (missing // len(DIGITS) + 1))[:missing]
    return PAD.sub(replace, value)

DATE = re.compile(r"\{date:\+(\d+)d\}")

# The registry of the German domains (DENIC) counts its days in this zone.
REGISTRY_ZONE = ZoneInfo("Europe/Berlin")

def replace_date_placeholders(value: str, today: date | None = None) -> str:
    """Replaces {date:+Nd} by the date N days from today (YYYY-MM-DD, the day of the registry's zone), for a date the
    registry limits to a period from now, such as the expiry of an authorisation information."""
    today = today or datetime.now(REGISTRY_ZONE).date()
    return DATE.sub(lambda match: (today + timedelta(days=int(match.group(1)))).isoformat(), value)

def response_matches(expected, response, test_name, signalling="header") -> bool:
    """Whether a response matches an `until`: the parts it states (status, body, fields, headers), and only those."""
    try:
        if "status" in expected:
            statuses = expected["status"] if isinstance(expected["status"], list) else [expected["status"]]
            assert response.status_code in statuses
        if "body" in expected or "fields" in expected:
            body = json.loads(response.text)
            if "body" in expected:
                recusive_compare_existing(test_name, "$", body, expected["body"], case_sensitive=False)
            for field, test in expected.get("fields", {}).items():
                assert evaluate_condition(field_value(body, field), test)
        assert_headers(expected.get("headers", {}), response, test_name)
    except (AssertionError, ValueError, TypeError):
        return False
    return True

def send_step(client, step, test_name, signalling="header", credentials=None, pacer=None, sleep=time.sleep):
    """Sends one prepared step (selectors, placeholders and captures resolved) and asserts its response, which it
    returns. Its `capture` and `until` are for the caller."""
    if step.get("delay_seconds"):
        sleep(step["delay_seconds"])
    headers = step["request"].get("headers", {})
    if pacer is not None:
        pacer.wait(headers)
    sent_headers = credentials.headers(headers) if credentials is not None else headers
    if "body_json" in step["request"]:
        response = client.request(step["request"]["method"], step["request"]["url"],
                                  json=step["request"]["body_json"], headers=sent_headers)
    elif "body_raw" in step["request"]:
        response = client.request(step["request"]["method"], step["request"]["url"],
                                  content=step["request"]["body_raw"], headers=sent_headers)
    else:
        response = client.request(step["request"]["method"], step["request"]["url"], headers=sent_headers)
    print(f"Test case: {test_name}: {response.status_code} - {response.headers} - {response.text}")

    assert_rpp_headers(step["request"].get("headers", {}), response, test_name)
    if "any_of" in step["response"]:
        assert_any_response(step["response"]["any_of"], response, test_name, signalling)
    else:
        assert_response(step["response"], response, test_name, signalling)
    return response

def take_captures(step, response, captures):
    """A step's "capture" maps a name to a dotted field of its response body, for {capture:name} in later steps."""
    for name, path in step.get("capture", {}).items():
        captures[name] = field_value(response.json(), path)

def endpoint_test(client, case_sequence, sleep=time.sleep, credentials=None, pacer=None):
    """
    Runs the steps of a case, each prepared already, against a test client.

    Args:
        client: The test client.
        case_sequence: The case, with its prepared steps.
        sleep: Waits for a step's "delay_seconds" before its request, for registry periods that must pass (the
            runner computes them from the step's `wait`; a case file does not write them).
        credentials: Replaces a `{auth:…}` header by the credential when the request is sent, so the case never
            holds one (`tests.helper.test_environment.Credentials`).
        pacer: Waits before a request of a registrar so its requests stay under the backend's limit.
    """
    if "skip" in case_sequence:
        pytest.skip(reason=f"Skipping test case: {case_sequence['test_id']} - {case_sequence['skip']}")
    captures = {}
    signalling = credentials.env.preset_signalling if credentials is not None else "header"
    for i, step in enumerate(case_sequence["steps"]):
        step = substitute_captures(step, captures)
        response = send_step(client, step, f"{case_sequence['test_id']}[{i}]", signalling, credentials, pacer, sleep)
        take_captures(step, response, captures)
