import datetime
import json
import os
import re
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from main import app
from tests.helper import selectors
from tests.helper.idn_labels import replace_idn_placeholders
from tests.helper.integration_api_test import endpoint_test, replace_pad_placeholders, replace_upper_placeholders
from tests.helper.pacer import Pacer
from tests.helper.test_environment import (
    REPOSITORY, Credentials, EnvironmentError, environment_names, load, replace_values, selected_name,
)

app.app.config.update({
        "TESTING": True,
    })

# The credentials of the test environment come from .env in the repository root, or from the process environment,
# which wins. The proxy never reads .env.
load_dotenv(REPOSITORY / ".env", override=False)
environment = load(selected_name())
workers = int(os.getenv("PYTEST_XDIST_WORKER_COUNT", "1"))
if workers > environment.max_workers:
    raise EnvironmentError(f"{environment.name} allows at most {environment.max_workers} workers, the run has {workers}")
credentials = Credentials(environment)
pacer = Pacer(environment.rpp_requests_per_minute, workers, credentials.slot)
facts = selectors.Facts(app.app.config["RPP_BACKEND_PROFILE"], environment.facts)

# The facts of every known environment, from the profile its descriptor names, to find a case that runs nowhere.
all_facts = {name: selectors.Facts(env.declared_profile(), env.facts)
             for name in environment_names()
             for env in [load(name, with_credentials=False)]}
all_facts[environment.name] = facts  # the app under test may offer more than its declared profile, such as LGRs

# --- Test Client Fixture ---
@pytest.fixture(scope='module')
def client():
    """Provides a test client for the Flask application."""
    with app.test_client() as c:
        yield c # The test client instance


random_name = str(uuid.uuid4()) # Generate a random name for testing
random_id_10 = str(uuid.uuid4())[:10]

GROUP_FILE = "_group.json"


def _natural_key(path: Path):
    """Sort key that orders test2 before test10 (numeric-aware)."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.stem)]


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _collect_test_cases(root: Path):
    """
    Discover every *.json test-case file under ``root/<group>/`` and return a
    list of case dicts.

    The parametrized test id is ``<test_group>-<test_id>`` (``test_id`` comes
    from inside each file). Files are visited in natural-numeric order so that
    test2 lists before test10. ``_group.json`` is not a case: its ``when`` applies
    to every case of the group.

    Files that cannot be parsed are NOT silently dropped: a sentinel case is
    emitted that fails loudly when run, so a broken file still shows up in the
    listing instead of vanishing. A selector that names no fact is such a file.
    """
    cases: list[dict] = []
    if not (root.exists() and root.is_dir()):
        return cases

    for subdir in sorted(root.iterdir(), key=lambda p: p.name.lower()):
        if not subdir.is_dir():
            continue
        group_when = None
        group_error = None
        if (subdir / GROUP_FILE).exists():
            try:
                group_when = _read_json(subdir / GROUP_FILE)["when"]
                for env_facts in [facts, *all_facts.values()]:
                    selectors.unmet(group_when, env_facts)
            except Exception as exc:  # noqa: BLE001 - surface, don't swallow
                group_error = f"{GROUP_FILE}: {type(exc).__name__}: {exc}"
        for json_file in sorted(subdir.glob("*.json"), key=_natural_key):
            if json_file.name == GROUP_FILE:
                continue
            try:
                if group_error:
                    raise ValueError(group_error)
                data = _read_json(json_file)
                for env_facts in [facts, *all_facts.values()]:
                    selectors.check(data, env_facts)
            except Exception as exc:  # noqa: BLE001 - surface, don't swallow
                cases.append({
                    "test_group": subdir.name,
                    "test_id": json_file.stem,
                    "_load_error": f"{type(exc).__name__}: {exc}",
                })
                continue

            data["test_group"] = subdir.name
            data.setdefault("test_id", json_file.stem)
            if group_when is not None:
                data["_group_when"] = group_when
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

def process_placeholders(json_data=dict|list|str|None, obj=None, started=None):
    """
    Recursively replace placeholders in the JSON data with actual values.
    """
    if obj is None and isinstance(json_data, dict) and "test_id" in json_data:
        obj = json_data
    if isinstance(json_data, dict):
        return {k: process_placeholders(v, obj, started) for k, v in json_data.items()} # type: ignore
    elif isinstance(json_data, list):
        return [process_placeholders(item, obj, started) for item in json_data] # type: ignore
    elif isinstance(json_data, str):
        replaced = json_data\
            .replace("{random_name}", f"{obj['test_group'].replace('_', '-')}-{random_name}" if "test_group" in obj else random_name)\
            .replace("{random_id_10}", f"{random_id_10}")\
            .replace("{test_start}", started.isoformat())# type: ignore
        replaced = replace_values(replaced, environment, random_id_10)
        replaced = replace_upper_placeholders(replace_pad_placeholders(replace_idn_placeholders(replaced, random_id_10)))
        return replaced.replace("{unique_cltrid}", str(uuid.uuid4())) # RPP-Cltrid is unique per request
    else:
        return json_data


def _case_selectors(case):
    return [w for w in (case.get("_group_when"), case.get("when")) if w is not None]


def unmet_case_selectors(case, case_facts) -> list[str]:
    return [reason for when in _case_selectors(case) for reason in selectors.unmet(when, case_facts)]


def select(case):
    """The case as the environment under test runs it: the steps whose `when` holds, each `select` resolved."""
    steps = [selectors.resolve({k: v for k, v in step.items() if k != "when"}, facts)
             for step in case["steps"] if "when" not in step or selectors.holds(step["when"], facts)]
    return {**{k: v for k, v in case.items() if k not in ("when", "_group_when")}, "steps": steps}


# --- Test Function ---
@pytest.mark.parametrize("case", test_cases, ids=test_ids) # type: ignore
def test_from_file_definition(client, case):
    if "_load_error" in case:
        pytest.fail(f"Could not load test case file: {case['_load_error']}")
    if "_duplicate_id" in case:
        pytest.fail(f"Duplicate test id: {case['_duplicate_id']} "
                    f"(two test-case files share <test_group>-<test_id>)")
    if all(unmet_case_selectors(case, env_facts) for env_facts in all_facts.values()):
        pytest.fail(f"The selectors skip this case in every environment ({', '.join(all_facts)}), so it never runs")
    unmet = unmet_case_selectors(case, facts)
    if unmet:
        pytest.skip(reason=f"skipped in {environment.name}: {'; '.join(unmet)}")
    # The selectors are resolved first, then the placeholders, then the captures.
    # {test_start} is the start of this case, so the time windows in the data do not depend on suite length.
    return endpoint_test(client, process_placeholders(select(case), started=datetime.datetime.now(datetime.UTC)),
                         credentials=credentials, pacer=pacer)
