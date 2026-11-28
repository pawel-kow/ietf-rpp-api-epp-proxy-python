"""The step runner of the integration cases: blocks, until-loops, failure locations and the teardown that goes on
(tests/helper/step_runner.py, #218)."""
import itertools
import json

import pytest

from tests.helper.step_runner import StepFailure, StepRunner


class Reply:
    def __init__(self, status, body, code, cltrid):
        self.status_code = status
        self.text = json.dumps(body)
        self.content = self.text.encode()
        headers = {"RPP-Svtrid": "sv", "RPP-Code": code, "RPP-Cltrid": cltrid}
        self.headers = {**headers, **{k.lower(): v for k, v in headers.items()}}  # read by either case, as Starlette's

    def json(self):
        return json.loads(self.text)


class Client:
    """Answers each request with the next (status, body, code) of its script, and records the URLs."""

    def __init__(self, *script):
        self.script = list(script)
        self.urls = []
        self.cltrids = []

    def request(self, method, url, headers=None, **_):
        self.urls.append(url)
        self.cltrids.append(headers.get("RPP-Cltrid"))
        status, body, code = self.script.pop(0)
        return Reply(status, body, code, headers.get("RPP-Cltrid"))


cltrids = itertools.count()


def prepare(item):
    """What the runner of the case files does to an item before it runs: here only a new clTRID per request."""
    if "when" in item:
        if item["when"] == "no":
            return None
        item = {k: v for k, v in item.items() if k != "when"}
    if "request" not in item:
        return item
    return {**item, "request": {**item["request"], "headers": {"RPP-Cltrid": f"cl-{next(cltrids)}"}}}


def step(url, status=200, **more):
    return {"comment": "c", "request": {"method": "GET", "url": url}, "response": {"status": status, **more}}


OK = (200, {}, "01000")


def runner(client):
    return StepRunner(client, prepare, "t1")


def test_the_steps_run_in_order_and_captures_carry_across_phases():
    client = Client((200, {"id": "m1"}, "01000"), OK, OK)
    run = runner(client)

    run.run([{**step("/a", body={}), "capture": {"id": "id"}}], "setup")
    run.run([step("/b/{capture:id}", body={})], "steps")
    assert run.run_teardown([step("/c/{capture:id}", body={})]) == []

    assert client.urls == ["/a", "/b/m1", "/c/m1"]


def test_a_block_runs_its_steps_and_a_capture_in_it_is_seen_after_it():
    client = Client((200, {"id": "m1"}, "01000"), OK)

    runner(client).run([{"block": [{**step("/a", body={}), "capture": {"id": "id"}}], "origin": "inc"},
                        step("/b/{capture:id}", body={})], "steps")

    assert client.urls == ["/a", "/b/m1"]


def test_an_item_whose_when_does_not_hold_is_left_out():
    client = Client(OK)

    runner(client).run([{"block": [step("/no")], "origin": "inc", "when": "no"}, step("/b", body={})], "steps")

    assert client.urls == ["/b"]


def drain():
    return {"loop": [
        {"comment": "c", "request": {"method": "GET", "url": "/messages"},
         "response": {"any_of": [{"status": 200, "body": []}, {"status": 200, "body": [{}]}]},
         "until": {"headers": {"RPP-Code": "01300"}}, "capture": {"head": "0.id"}},
        step("/messages/{capture:head}", body={}),
    ]}


def test_a_loop_repeats_until_its_step_matches_and_then_takes_no_capture():
    client = Client((200, [{"id": "1"}], "01301"), OK, (200, [{"id": "2"}], "01301"), OK, (200, [], "01300"), OK)

    runner(client).run([drain(), step("/after", body={})], "steps")

    assert client.urls == ["/messages", "/messages/1", "/messages", "/messages/2", "/messages", "/after"]


def bounded(limit):
    return {**drain(), "max_iterations": limit}


def test_a_loop_with_a_bound_fails_when_it_does_not_end_within_it():
    client = Client((200, [{"id": "1"}], "01301"), OK, (200, [{"id": "2"}], "01301"), OK, (200, [], "01300"))

    with pytest.raises(StepFailure, match=r"t1 steps\[0\]: the loop did not end in 2 iterations"):
        runner(client).run([bounded(2)], "steps")

    assert client.urls == ["/messages", "/messages/1", "/messages", "/messages/2"]       # no third iteration


def test_a_loop_with_a_bound_ends_on_its_until_in_the_last_iteration_allowed():
    runner(Client((200, [{"id": "1"}], "01301"), OK, (200, [], "01300"), OK)).run([bounded(2), step("/after", body={})], "steps")


def test_each_iteration_prepares_its_steps_again_so_the_cltrid_is_new():
    client = Client((200, [{"id": "1"}], "01301"), OK, (200, [], "01300"))

    runner(client).run([drain()], "steps")

    assert len(set(client.cltrids)) == 3


def test_a_loop_whose_until_matches_at_once_runs_its_step_once():
    client = Client((200, [], "01300"))

    runner(client).run([drain()], "steps")

    assert client.urls == ["/messages"]


def test_the_until_step_must_still_pass_its_response():
    client = Client((500, [], "01300"))

    with pytest.raises(StepFailure, match=r"t1 steps\[0\] > loop iteration 1\[0\]"):
        runner(client).run([drain()], "steps")


def test_a_failure_names_the_phase_the_include_and_the_loop_iteration():
    client = Client(OK, (200, [{"id": "1"}], "01301"), OK, (200, [{"id": "2"}], "01301"), (404, {}, "02303"))

    with pytest.raises(StepFailure) as failed:
        runner(client).run([step("/first", body={}), {"block": [drain()], "origin": "drain_queue"}], "setup")

    assert str(failed.value).startswith("t1 setup[1] > include drain_queue[0] > loop iteration 2[1]: ")


def test_a_failure_is_a_step_failure_an_assertion_error():
    client = Client((404, {}, "02303"))

    with pytest.raises(AssertionError):
        runner(client).run([step("/x", body={})], "steps")


def test_the_teardown_goes_on_after_a_failing_step_and_returns_the_failures():
    client = Client((404, {}, "02303"), OK, (404, {}, "02303"), OK)

    warnings = runner(client).run_teardown([
        step("/a", body={}),
        {"block": [step("/b", body={}), step("/c", body={})], "origin": "inc"},
        step("/d", body={}),
    ])

    assert client.urls == ["/a", "/b", "/c", "/d"]
    assert [w.split(":")[0] for w in warnings] == ["t1 teardown[0]", "t1 teardown[1] > include inc[1]"]


def test_a_failure_in_a_teardown_loop_ends_the_loop_and_the_teardown_goes_on():
    client = Client((200, [{"id": "1"}], "01301"), (404, {}, "02303"), OK)

    warnings = runner(client).run_teardown([drain(), step("/after", body={})])

    assert client.urls == ["/messages", "/messages/1", "/after"]
    assert len(warnings) == 1 and warnings[0].startswith("t1 teardown[0] > loop iteration 1[1]: ")


def test_a_missing_capture_in_the_teardown_is_a_warning_too():
    client = Client(OK)

    warnings = runner(client).run_teardown([step("/x/{capture:never}", body={}), step("/y", body={})])

    assert client.urls == ["/y"] and "never" in warnings[0]
