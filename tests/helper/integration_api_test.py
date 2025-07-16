from .recursive_compare_existing import recusive_compare_existing
import json
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

def endpoint_test(client, case_sequence):
    """
    Tests the POST /domains endpoint using the Flask test client.

    Args:
        client: The Flask test client fixture.
        cases: A sequence of test steps as parameterized test case dictionaries.
    """
    if "skip" in case_sequence:
        pytest.skip(reason=f"Skipping test case: {case_sequence['test_id']} - {case_sequence['skip']}")
    for i, case in enumerate(case_sequence["steps"]):
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

        # --- Assertions ---
        # 1. Check the HTTP status code
        if isinstance(case["response"]["status"], list):
            # Check if the response status code is in the list of expected status codes
            assert response.status_code in case["response"]["status"], f"Unexpected status code for test case: {case_sequence['test_id']}[{i}]"
        else:
            assert response.status_code == case["response"]["status"]

        if "content_type" in case["response"]:
            # Check the Content-Type header
            assert response.headers["Content-Type"].lower() == case["response"]["content_type"].lower(), f"Content-Type mismatch for test case: {case_sequence['test_id']}[{i}]"

        # 2. Check the response body (if one is expected)
        if "body" in case["response"]:
            # For JSON responses, compare the parsed JSON
            try:
                response_json = json.loads(response.text)
            except json.JSONDecodeError:
                # If JSON decoding fails, log the response text for debugging
                assert False, f"Failed to decode JSON for test case: {case_sequence['test_id']}[{i}] Response Text: {response.text}"
            assert response_json is not None, f"Response body was not valid JSON for test case: {case_sequence['test_id']}[{i}]"
            # Check if the response JSON matches the expected structure
            recusive_compare_existing(f"{case_sequence['test_id']}[{i}]", "$", response_json, case["response"]["body"], case_sensitive=False)
            # Check for expected fields in the response
            # Ensure that the expected fields are present and not null
            if "fields" in case["response"]:
                for field, test in case["response"]["fields"].items():
                    assert field in response_json, f"Field '{field}' not found in response for test case: {case_sequence['test_id']}[{i}]"
                    if callable(test):
                        assert test(response_json[field]), f"Field '{field}' is not valid for test case: {case_sequence['test_id']}[{i}]"
                    elif isinstance(test, dict) and "type" in test:
                        assert evaluate_condition(response_json[field], test), f"Field '{field}' does not meet the condition {test[type]} for test case: {case_sequence['test_id']}[{i}]"
                    else:
                        raise ValueError(f"Field '{field}' has unexpected type or value for test case: {case_sequence['test_id']}[{i}]")
            # Check for expected headers in the response
            if "headers" in case["response"]:
                # Check for expected headers in the response
                for header, test in case["response"]["headers"].items():
                    if test is not None:
                        assert header in response.headers, f"Header '{header}' not found in response for test case: {case_sequence['test_id']}[{i}]"
                        if isinstance(test, str):
                            assert response.headers[header] == test, f"Header '{header}' has unexpected value for test case: {case_sequence['test_id']}[{i}]"
                        elif callable(test):
                            assert test(response.headers[header]), f"Header '{header}' is not valid for test case: {case_sequence['test_id']}[{i}]"
                        elif isinstance(test, dict) and "type" in test:
                            assert evaluate_condition(response.headers[header], test), f"Header '{header}' does not meet the condition {test['type']} for test case: {case_sequence['test_id']}[{i}]"
                        else:
                            raise ValueError(f"Header '{header}' has unexpected type or value for test case: {case_sequence['test_id']}[{i}]")
                    else:
                        assert header not in response.headers, f"Header '{header}' should not be present in response for test case: {case_sequence['test_id']}[{i}]"
        else:
            # For responses expected to have no body (like 100, 204)
            assert not response.content, "Response data not expected" # Check if data attribute is empty

