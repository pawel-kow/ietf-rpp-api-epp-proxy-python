# Testing

Project-agnostic testing rules. Commands, test layout and environment are in
[testing.project.md](testing.project.md).

## Test-driven development

**TDD, always.** Write failing tests first:

1. Add the test.
2. Create stubs so imports resolve. A missing-module error is not a useful
   failure signal.
3. Confirm the failure shows the actual gap.
4. Only then implement.

This applies to bug fixes (reproduce first) and behaviour changes alike.

**The test suite is the only success oracle.** Success is asserted by the
project's test suite, never by ad-hoc scripts. If the tests needed to assert a
change are missing, write them before the change.

## Writing tests

- **The spec is the oracle, not the code.** Where a normative spec exists, derive
  expected values from it rather than encoding what the code currently returns. A
  test written to the spec will legitimately fail against a buggy implementation
  and point at the bug.
- **Assert the contract, not just the outcome.** Error-path tests pin the exact
  error code, not only the broad status. "An error occurred" is not an assertion.
- **Probe real dependencies before asserting.** Where behaviour depends on an
  external system, observe it first instead of guessing. Delete any throwaway
  probes afterwards.
- **One facet per test.** Prefer narrow cases over only large multi-step scenarios,
  because they localise regressions.
- **Keep tests repeatable.** Tests against shared systems use unique generated
  data so that reruns do not collide.
- **Keep tests independent.** No test relies on another one or on their order, so
  the suite can run in parallel.

## Design for testability

Pass dependencies in rather than constructing them internally. Tests use plain
test-double classes, not patching or mocking frameworks.
