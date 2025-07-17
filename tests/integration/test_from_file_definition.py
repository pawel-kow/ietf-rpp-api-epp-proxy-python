import pytest
import connexion
import json
import uuid
from run import app
import datetime
from tests.helper.integration_api_test import endpoint_test
from tests.helper.check_datetime import check_datetime_format_utc_and_delta
import os
from pathlib import Path


app.app.config.update({
        "TESTING": True,
    })

# --- Test Client Fixture ---
@pytest.fixture(scope='module')
def client():
    """Provides a test client for the Flask application."""
    with app.test_client() as c:
        yield c # The test client instance


random_name = str(uuid.uuid4()) # Generate a random name for testing
test_start = datetime.datetime.now(datetime.UTC)

test_cases = []

test_case_data_dir = Path("./tests/integration/test_case_data")
if test_case_data_dir.exists() and test_case_data_dir.is_dir():
    for subdir in sorted(test_case_data_dir.iterdir()):
        if subdir.is_dir():
            for json_file in sorted(subdir.glob("*.json")):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                        data["test_group"] = subdir.name
                        test_cases.append(data)
                except Exception:
                    pass  # Ignore invalid JSON files

def process_placeholders(json_data):
    """
    Recursively replace placeholders in the JSON data with actual values.
    """
    if isinstance(json_data, dict):
        return {k: process_placeholders(v) for k, v in json_data.items()}
    elif isinstance(json_data, list):
        return [process_placeholders(item) for item in json_data]
    elif isinstance(json_data, str):
        return json_data\
            .replace("{random_name}", random_name)\
            .replace("{test_start}", test_start.isoformat())
    else:
        return json_data


# --- Test Function ---
@pytest.mark.parametrize("case", process_placeholders(test_cases), ids=[f"{c["test_group"]}-{c["test_id"]}" for c in test_cases])
def test_from_file_definition(client, case):
    return endpoint_test(client, case)