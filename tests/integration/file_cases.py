"""The data-driven integration cases: loading a case file and running it against the app under test.

`conftest.py` of this directory collects every `test_case_data/<group>/<case>.json` as a pytest item, so the test tree
follows the data folders; this module holds what those items run, and is not itself a test module.
"""
import datetime
import json
import os
import re
import uuid
from pathlib import Path

import pytest
from dotenv import load_dotenv

from main import app
from tests.helper import durations, selectors
from tests.helper.idn_labels import replace_idn_placeholders
from tests.helper.integration_api_test import endpoint_test, replace_pad_placeholders, replace_upper_placeholders
from tests.helper.pacer import Pacer
from tests.helper.test_environment import (
    REPOSITORY, Credentials, EnvironmentError, environment_names, load, replace_fact, replace_values, selected_name,
)

CASE_DATA = Path(__file__).parent / "test_case_data"
GROUP_FILE = "_group.json"

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
# The longest wait of this run, and the buffer of each wait (tests/helper/durations.py); the facts of the other
# environments wait without limit, so a long wait does not make a case look as if it ran nowhere.
facts = selectors.Facts(app.app.config["RPP_BACKEND_PROFILE"], environment.facts, durations.max_wait(),
                        durations.buffer_percent())

# The facts of every known environment, with the profile of its config, to find a case that runs nowhere.
all_facts = {name: selectors.Facts(env.profile, env.facts, None, durations.buffer_percent())
             for name in environment_names()
             for env in [load(name, with_credentials=False)]}
all_facts[environment.name] = selectors.Facts(  # the app under test may be given another config by RPP_CONFIG_FILE
    facts.profile, facts.env_facts, None, facts.buffer_percent)


random_name = str(uuid.uuid4()) # Generate a random name for testing
random_id_10 = str(uuid.uuid4())[:10]


def natural_key(path: Path):
    """Sort key that orders test2 before test10 (numeric-aware)."""
    return [int(part) if part.isdigit() else part.lower()
            for part in re.split(r"(\d+)", path.stem)]


def _read_json(path: Path):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_group_when(group_dir: Path):
    """The `when` of the group's `_group.json`, checked against every environment, or None without one.

    Raises when the file cannot be read or names a fact no environment has; every case of the group then fails.
    """
    if not (group_dir / GROUP_FILE).exists():
        return None
    group_when = _read_json(group_dir / GROUP_FILE)["when"]
    for env_facts in [facts, *all_facts.values()]:
        selectors.unmet(group_when, env_facts)
    return group_when


def load_case(path: Path, group_when):
    """The case of a file, with its `test_group`, `test_id` and the `when` of its group.

    Raises when the file cannot be read or a selector names no fact; the case then fails when run, so a broken file
    still shows up instead of vanishing.
    """
    data = _read_json(path)
    for env_facts in [facts, *all_facts.values()]:
        selectors.check(data, env_facts)
    data["test_group"] = path.parent.name
    data.setdefault("test_id", path.stem)
    if group_when is not None:
        data["_group_when"] = group_when
    return data


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
        one_of = replace_fact(json_data, environment)
        if not isinstance(one_of, str):
            return one_of
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


def _with_wait(step):
    """A step's `wait`, the periods it waits for, as the seconds the runner sleeps before its request."""
    paths = selectors.wait_paths(step)
    step = {k: v for k, v in step.items() if k != "wait"}
    if paths:
        step["delay_seconds"] = sum(facts.wait_seconds(path) for path in paths)
    return step


def select(case):
    """The case as the environment under test runs it: the steps whose `when` holds, each `select` resolved."""
    steps = [_with_wait(selectors.resolve({k: v for k, v in step.items() if k != "when"}, facts))
             for step in case["steps"] if "when" not in step or selectors.holds(step["when"], facts)]
    return {**{k: v for k, v in case.items() if k not in ("when", "_group_when")}, "steps": steps}


def run_case(case):
    """Runs a loaded case in a test client of its own, or skips it where its selectors do not hold."""
    if all(unmet_case_selectors(case, env_facts) for env_facts in all_facts.values()):
        pytest.fail(f"The selectors skip this case in every environment ({', '.join(all_facts)}), so it never runs")
    unmet = unmet_case_selectors(case, facts)
    if unmet:
        pytest.skip(reason=f"skipped in {environment.name}: {'; '.join(unmet)}")
    # The selectors are resolved first, then the placeholders, then the captures.
    # {test_start} is the start of this case, so the time windows in the data do not depend on suite length.
    with app.test_client() as client:
        endpoint_test(client, process_placeholders(select(case), started=datetime.datetime.now(datetime.UTC)),
                      credentials=credentials, pacer=pacer)
