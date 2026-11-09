from .recursive_compare_existing import recusive_compare_existing
import json
import re
import pytest
from datetime import datetime, timezone
from tests.helper.check_datetime import check_datetime_format_utc_and_delta

def evaluate_condition(value, spec):
    if spec["type"] == "not_null":
        return value is not None
    elif spec["type"] == "not_empty_string":
        return isinstance(value, str) and value != ""
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
            assert response.headers[header] == test, f"Header '{header}' has unexpected value for test case: {test_name}"
        elif isinstance(test, dict) and "type" in test:
            assert evaluate_condition(response.headers[header], test), f"Header '{header}' does not meet the condition {test['type']} for test case: {test_name}"
        else:
            raise ValueError(f"Header '{header}' has unexpected type or value for test case: {test_name}")

def assert_response(expected, response, test_name):
    # 1. Check the HTTP status code
    if isinstance(expected["status"], list):
        # Check if the response status code is in the list of expected status codes
        assert response.status_code in expected["status"], f"Unexpected status code for test case: {test_name}"
    else:
        assert response.status_code == expected["status"]

    if "content_type" in expected:
        # Check the Content-Type header
        assert response.headers["Content-Type"].lower() == expected["content_type"].lower(), f"Content-Type mismatch for test case: {test_name}"

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

def assert_any_response(alternatives, response, test_name):
    """Passes when one alternative matches, for behaviour the protocol leaves to the server."""
    failures = []
    for i, expected in enumerate(alternatives):
        try:
            assert_response(expected, response, test_name)
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

def endpoint_test(client, case_sequence):
    """
    Tests the POST /domains endpoint using the Flask test client.

    Args:
        client: The Flask test client fixture.
        cases: A sequence of test steps as parameterized test case dictionaries.
    """
    if "skip" in case_sequence:
        pytest.skip(reason=f"Skipping test case: {case_sequence['test_id']} - {case_sequence['skip']}")
    captures = {}
    for i, case in enumerate(case_sequence["steps"]):
        case = substitute_captures(case, captures)
        # --- Make HTTP Request ---
        if "body_json" in case["request"]:
            response = client.request(case["request"]["method"],
                                    case["request"]["url"],
                                    json=case["request"]["body_json"],
                                    headers=case["request"]["headers"])
        elif "body_raw" in case["request"]:
            response = client.request(case["request"]["method"],
                                    case["request"]["url"],
                                    content=case["request"]["body_raw"],
                                    headers=case["request"]["headers"])
        else:
            response = client.request(case["request"]["method"],
                                    case["request"]["url"],
                                    headers=case["request"]["headers"])
        print(f"Test case: {case_sequence['test_id']}[{i}]: {response.status_code} - {response.headers} - {response.text}")

        test_name = f"{case_sequence['test_id']}[{i}]"
        assert_rpp_headers(case["request"]["headers"], response, test_name)
        if "any_of" in case["response"]:
            assert_any_response(case["response"]["any_of"], response, test_name)
        else:
            assert_response(case["response"], response, test_name)

        # A step's "capture" maps a name to a dotted field of its response body, for {capture:name} in later steps.
        for name, path in case.get("capture", {}).items():
            captures[name] = field_value(response.json(), path)
