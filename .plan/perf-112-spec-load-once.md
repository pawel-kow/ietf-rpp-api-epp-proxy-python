# Plan: unit tests are slow (#112)

Branch `perf/112-spec-load-once` from `main` (a63b339).

## Tasks

- [~] Maintainer accepts the approach (step 1 below; step 2 only if step 1 is not enough)
- [ ] Measure the baseline: `pytest -n 4 tests/unit` wall and CPU, and the slow tests named in #112
- [ ] Failing test: building two apps parses `openapi.yaml` once
- [ ] `src/app.py`: parse `openapi.yaml` once per process with `yaml.CSafeLoader`, give `add_api` a deep copy
- [ ] Measure again, record the numbers here and in the PR
- [ ] Full `pytest -n 8`
- [ ] Draft PR

## Findings

- Profiled `test_contact_transfer_wire.py::test_create_with_a_read_only_member_is_a_400_without_epp`:
  33.5 s, of which 31.7 s are in 6 calls of `create_app` → connexion `add_api` → `Specification.load`.
  Request handling is negligible.
- One `create_app` takes about 1.33 s without the profiler:
  - `yaml.safe_load` of the 30,788-line `openapi.yaml`: about 0.80 s (pure-Python loader).
  - `yaml.CSafeLoader` of the same file: 0.15 s, equal result (libyaml is installed).
  - connexion `Specification.from_dict` (deepcopy, spec schema validation, `$ref` resolution): about 0.50 s.
  - Building the middleware stack on the first request: about 0.04 s; later requests about 1 ms.
- `openapi.yaml` has no external `$ref` and no Jinja syntax, so passing a dict instead of the path is equivalent.
- connexion 3.2 `add_api` accepts a path, URL or dict only, not a built `Specification`, so the validation cost
  cannot be shared without sharing apps between tests.

## Decisions

- Step 1: cache the parsed spec dict per process in `src/app.py`, deep-copy it per app. Each test still gets its
  own app, so no state is shared. Expected: about 1.33 s → 0.55 s per app.
- Step 2 (only if step 1 is not enough, needs separate acceptance): one app per test module with a per-test
  swappable fake backend. Shares app state between tests, which #112 asks to avoid.

## Corrections

## Open questions

- Passing a dict means `uvicorn --reload` no longer watches `openapi.yaml`. Acceptable?
- PRs #118 (#116) and #121 (#117) change `create_app`'s signature and are not on `main` yet; this branch will
  need a small rebase over whichever merges first.
