import json

def _matches(case, path, actual_data, expected_data, case_sensitive):
    try:
        recusive_compare_existing(case, path, actual_data, expected_data, case_sensitive=case_sensitive)
    except (AssertionError, TypeError):
        return False
    return True

def _pairs_up(case, path, actual_data, expected_data, case_sensitive):
    """Lists are unordered: every expected element needs an actual element of its own, and may be partial."""
    if not expected_data:
        return True
    return any(
        _matches(case, path, element, expected_data[0], case_sensitive)
        and _pairs_up(case, path, actual_data[:i] + actual_data[i + 1:], expected_data[1:], case_sensitive)
        for i, element in enumerate(actual_data)
    )

def recusive_compare_existing(case, path, actual_data, expected_data, case_sensitive=True):
    """
    Recursively traverses a dictionary or list (representing JSON) and compares if values of existing_data are present and equal actual_data.
    """

    if isinstance(expected_data, dict):
        for key, value in expected_data.items():
            assert key in actual_data, f"Case {case}. Path: {path}. Key '{key}' not found in actual_data."
            recusive_compare_existing(case, f"{path}.{key}", actual_data[key], value, case_sensitive=case_sensitive) # Recurse/process value
    elif isinstance(expected_data, list):
        assert len(actual_data) == len(expected_data), f"Case {case}. Path: {path}. Length of actual_data and expected_data lists do not match."
        assert _pairs_up(case, path, actual_data, expected_data, case_sensitive), f"Case {case}. Path: {path}. {json.dumps(actual_data)} does not match {json.dumps(expected_data)}."
    else:
        if isinstance(actual_data, str) and isinstance(expected_data, str):
            if case_sensitive:
                assert actual_data == expected_data, f"Case {case}. Path: {path}. Value '{actual_data}' does not match expected value '{expected_data}' (string case sensitive)."
            else:
                assert actual_data.lower() == expected_data.lower(), f"Case {case}. Path: {path}. Value '{actual_data}' does not match expected value '{expected_data}' (string case insensitive)."
        else:
            assert actual_data == expected_data, f"Case {case}. Path: {path}. Value '{actual_data}' does not match expected value '{expected_data}'."
