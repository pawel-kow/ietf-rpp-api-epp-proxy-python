from typing import List
import pytest
import connexion
import json
import uuid
import re
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
random_id_10 = str(uuid.uuid4())[:10]
test_start = datetime.datetime.now(datetime.UTC)

def _natural_key(path: Path):
    """Sort key that orders test2 before test10 (numeric-aware)."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.stem)]


def _collect_test_cases(root: Path):
    """
    Discover every *.json test-case file under ``root/<group>/`` and return a
    list of case dicts.

    The parametrized test id is ``<test_group>-<test_id>`` (``test_id`` comes
    from inside each file). Files are visited in natural-numeric order so that
    test2 lists before test10.

    Files that cannot be parsed are NOT silently dropped: a sentinel case is
    emitted that fails loudly when run, so a broken file still shows up in the
    listing instead of vanishing.
    """
    cases: list[dict] = []
    if not (root.exists() and root.is_dir()):
        return cases

    for subdir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not subdir.is_dir():
            continue
        for json_file in sorted(subdir.glob("*.json"), key=_natural_key):
            try:
                with open(json_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as exc:  # noqa: BLE001 - surface, don't swallow
                cases.append({
                    "test_group": subdir.name,
                    "test_id": json_file.stem,
                    "_load_error": f"{type(exc).__name__}: {exc}",
                })
                continue

            data["test_group"] = subdir.name
            data.setdefault("test_id", json_file.stem)
            cases.append(data)

    return cases


test_cases = _collect_test_cases(Path("./tests/integration/test_case_data"))

# Build the parametrize ids from <test_group>-<test_id>. Duplicate ids must not
# be silently coalesced/dropped by pytest — instead, tag every case sharing a
# duplicated id so it FAILS individually (see the sentinel check in the test),
# while making the pytest id unique enough that both are still listed and run.
_id_counts: dict[str, int] = {}
for _case in test_cases:
    _base_id = f'{_case["test_group"]}-{_case["test_id"]}'
    _id_counts[_base_id] = _id_counts.get(_base_id, 0) + 1

test_ids = []
_seen_counts: dict[str, int] = {}
for _case in test_cases:
    _base_id = f'{_case["test_group"]}-{_case["test_id"]}'
    if _id_counts[_base_id] > 1:
        _case["_duplicate_id"] = _base_id
        _seen_counts[_base_id] = _seen_counts.get(_base_id, 0) + 1
        test_ids.append(f"{_base_id}#{_seen_counts[_base_id]}")
    else:
        test_ids.append(_base_id)

def process_placeholders(json_data=dict|list|str|None, obj=None):
    """
    Recursively replace placeholders in the JSON data with actual values.
    """
    if obj is None and isinstance(json_data, dict) and "test_id" in json_data:
        obj = json_data
    if isinstance(json_data, dict):
        return {k: process_placeholders(v, obj) for k, v in json_data.items()} # type: ignore
    elif isinstance(json_data, list):
        return [process_placeholders(item, obj) for item in json_data] # type: ignore
    elif isinstance(json_data, str):
        return json_data\
            .replace("{random_name}", f"{obj['test_group'].replace('_', '-')}-{random_name}" if "test_group" in obj else random_name)\
            .replace("{random_id_10}", f"{random_id_10}")\
            .replace("{test_start}", test_start.isoformat())# type: ignore
    else:
        return json_data


# --- Test Function ---
@pytest.mark.parametrize("case", process_placeholders(test_cases), ids=test_ids) # type: ignore
def test_from_file_definition(client, case):
    if "_load_error" in case:
        pytest.fail(f"Could not load test case file: {case['_load_error']}")
    if "_duplicate_id" in case:
        pytest.fail(f"Duplicate test id: {case['_duplicate_id']} "
                    f"(two test-case files share <test_group>-<test_id>)")
    return endpoint_test(client, case)