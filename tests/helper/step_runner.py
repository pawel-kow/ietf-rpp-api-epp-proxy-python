"""Runs the items of a phase of a case: steps, blocks (an expanded include) and until-loops.

An item is prepared right before it runs (`prepare`: its `when`, selects, wait and placeholders), so a step a loop
repeats gets a new `{unique_cltrid}` each time. The captures are one namespace for all phases of the case.

A failure is a `StepFailure` whose message starts with where it happened, `t1 setup[2] > include drain_queue[0] >
loop iteration 7[1]: …`. `run` stops at the first one; `run_teardown` records it and goes on with the next item (a
failure inside a loop ends that loop), and returns what failed.
"""
import time

import pytest

from tests.helper.integration_api_test import response_matches, send_step, substitute_captures, take_captures

FAILURES = (Exception, pytest.fail.Exception)


class StepFailure(AssertionError):
    """A step that failed, with where it happened at the start of the message."""


class _UntilReached(Exception):
    """The `until` of the innermost loop matched: the loop ends."""


class StepRunner:
    def __init__(self, client, prepare, test_id: str, signalling: str = "header", credentials=None, pacer=None,
                 sleep=time.sleep):
        """`prepare(item)` is the item as it runs, or None when its `when` does not hold."""
        self.client = client
        self.prepare = prepare
        self.test_id = test_id
        self.signalling = signalling
        self.credentials = credentials
        self.pacer = pacer
        self.sleep = sleep
        self.captures = {}
        self.failures: list[str] | None = None  # collects the failures in the teardown, which goes on after them

    def run(self, items: list, phase: str) -> None:
        self._items(items, [phase], in_loop=False)

    def run_teardown(self, items: list, phase: str = "teardown") -> list[str]:
        self.failures = []
        try:
            self._items(items, [phase], in_loop=False)
            return self.failures
        finally:
            self.failures = None

    def _items(self, items: list, where: list[str], in_loop: bool) -> None:
        for i, item in enumerate(items):
            here = [*where[:-1], f"{where[-1]}[{i}]"]
            try:
                self._item(item, here)
            except StepFailure as failure:
                if self.failures is None or in_loop:
                    raise
                self.failures.append(str(failure))

    def _item(self, item: dict, here: list[str]) -> None:
        try:
            prepared = self.prepare(item)
        except FAILURES as exc:
            raise self._failure(here, exc) from exc
        if prepared is None:
            return
        if "block" in prepared:
            self._items(prepared["block"], [*here, f"include {prepared.get('origin')}"], in_loop=False)
        elif "loop" in prepared:
            self._loop(prepared["loop"], here, prepared.get("max_iterations"))
        else:
            self._step(prepared, here)

    def _loop(self, items: list, here: list[str], max_iterations: int | None = None) -> None:
        """Runs the items until the `until` step matches. With `max_iterations` the loop fails after that many iterations that did
        not end it, instead of running on."""
        iteration = 0
        while True:
            if max_iterations is not None and iteration >= max_iterations:
                raise StepFailure(f"{self.test_id} {' > '.join(here)}: the loop did not end in {max_iterations} iterations")
            iteration += 1
            try:
                self._items(items, [*here, f"loop iteration {iteration}"], in_loop=True)
            except _UntilReached:
                return

    def _step(self, step: dict, here: list[str]) -> None:
        name = f"{self.test_id} {' > '.join(here)}"
        try:
            step = substitute_captures(step, self.captures)
            response = send_step(self.client, step, name, self.signalling, self.credentials, self.pacer, self.sleep)
            if "until" in step and response_matches(step["until"], response, name, self.signalling):
                raise _UntilReached()
            take_captures(step, response, self.captures)
        except _UntilReached:
            raise
        except FAILURES as exc:
            raise self._failure(here, exc) from exc

    def _failure(self, here: list[str], exc: BaseException) -> StepFailure:
        if isinstance(exc, StepFailure):
            return exc
        message = getattr(exc, "msg", None) or str(exc) or type(exc).__name__
        return StepFailure(f"{self.test_id} {' > '.join(here)}: {message}")
