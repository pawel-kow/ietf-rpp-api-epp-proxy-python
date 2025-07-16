import json

def recusive_compare_existing(case, path, actual_data, expected_data, case_sensitive=True):
    """
    Recursively traverses a dictionary or list (representing JSON) and compares if values of existing_data are present and equal actual_data.
    """

    if isinstance(expected_data, dict):
        for key, value in expected_data.items():
            assert key in actual_data, f"Case {case}. Path: {path}. Key '{key}' not found in actual_data."
            recusive_compare_existing(case, f"{path}.{key}", actual_data[key], value, case_sensitive=case_sensitive) # Recurse/process value
    elif isinstance(expected_data, list):
        assert len(actual_data) == len(expected_data), "Case {case}. Path: {path}. Length of actual_data and expected_data lists do not match."
        ads = sorted(actual_data, key=lambda x: json.dumps(x, sort_keys=True))
        exps = sorted(expected_data, key=lambda x: json.dumps(x, sort_keys=True))
        for i, element in enumerate(exps):
            recusive_compare_existing(case, f"{path}[{i}]", ads[i], element)
    else:
        if isinstance(actual_data, str) and isinstance(expected_data, str):
            if case_sensitive:
                assert actual_data == expected_data, f"Case {case}. Path: {path}. Value '{actual_data}' does not match expected value '{expected_data}' (string case sensitive)."
            else:
                assert actual_data.lower() == expected_data.lower(), f"Case {case}. Path: {path}. Value '{actual_data}' does not match expected value '{expected_data}' (string case insensitive)."
        else:
            assert actual_data == expected_data, f"Case {case}. Path: {path}. Value '{actual_data}' does not match expected value '{expected_data}'."
