from .recursive_compare_existing import recusive_compare_existing
import json

def endpoint_test(client, case):
    """
    Tests the POST /domains endpoint using the Flask test client.

    Args:
        client: The Flask test client fixture.
        case: The parameterized test case dictionary.
    """
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
    print(f"Test case: {case['test_id']}: {response.status_code} - {response.headers} - {response.text}")

    # --- Assertions ---
    # 1. Check the HTTP status code
    assert response.status_code == case["response"]["status"]
    
    if "content_type" in case["response"]:
        # Check the Content-Type header
        assert response.headers["Content-Type"].lower() == case["response"]["content_type"].lower(), f"Content-Type mismatch for test case: {case['test_id']}"

    # 2. Check the response body (if one is expected)
    if "body" in case["response"]:
        # For JSON responses, compare the parsed JSON
        try:
            response_json = json.loads(response.text)
        except json.JSONDecodeError:
            # If JSON decoding fails, log the response text for debugging
            assert False, f"Failed to decode JSON for test case: {case['test_id']} Response Text: {response.text}"
        assert response_json is not None, f"Response body was not valid JSON for test case: {case['test_id']}"
        # Check if the response JSON matches the expected structure
        recusive_compare_existing(case['test_id'], "$", response_json, case["response"]["body"])
        # Check for expected fields in the response
        # Ensure that the expected fields are present and not null
        if "fields" in case["response"]:
            for field, fun in case["response"]["fields"].items():
                assert field in response_json, f"Field '{field}' not found in response for test case: {case['test_id']}"
                assert fun(response_json[field]), f"Field '{field}' is not valid for test case: {case['test_id']}"
    else:
        # For responses expected to have no body (like 100, 204)
        assert not response.data # Check if data attribute is empty

