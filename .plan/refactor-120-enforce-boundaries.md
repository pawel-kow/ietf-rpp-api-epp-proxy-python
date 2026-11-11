# Plan: enforce the module boundaries (#120, phase 1)

Branch `refactor/120-enforce-boundaries`. Phase 1 of #120: write the contracts into `architecture.project.md` and
check them with `import-linter`. No code in `src/` changes.

## Tasks

- [x] T1 `requirements-dev.txt` (`-r requirements.txt` + `import-linter`), installed in `.venv`
- [x] T2 `[tool.importlinter]` in `pyproject.toml`: one contract per rule, against today's package names
- [x] T3 `architecture.project.md`: target tree, dependency rules, "must never know", today → target mapping, the
      check; known debt for every `ignore_imports`
- [x] T4 `process.project.md`: setup with `requirements-dev.txt`, `lint-imports` in "Checks before done"
- [~] T5 `lint-imports` and full `pytest -n 8` green; draft PR

## Findings (evidence)

1. Imports per package today (grep of `src/`): `models` imports only the standard library; `registry` only
   `models`; `flows` `models` and `registry`; `controller` neither `eppclient` nor `epp_to_model_mapper`.
2. `epp_to_model_mapper/commands/helper.py` imports `config` at import time (#120 finding 2).

## Decisions

- D1 (maintainer) `import-linter` in a new `requirements-dev.txt`, so it stays out of the Docker image.
- D2 (maintainer) A separate `lint-imports` command in the documented checks, not a unit test.
- D3 (maintainer) Config in `pyproject.toml`.
- D4 (maintainer) Contracts against today's package names; each later phase renames them as it moves code. Today's
  violations are `ignore_imports`, listed as known debt, not fixed here.
- D5 import-linter cannot take the modules `app.py`, `config.py`, `run.py` as roots. `config` and `run` are
  forbidden by name (seen as external); what `app.py` and `run.py` import is checked from phase 4. Run as
  `PYTHONPATH=src lint-imports`, since import-linter puts only the working directory on the path.
- D6 Each contract was checked to break: an injected `flask` in `eppclient`, `config` in `flows` and `eppclient` in
  `controller` each broke the expected contracts, and removing the `ignore_imports` breaks
  `only-main-imports-settings`.
- D7 The devcontainer installs `requirements-dev.txt`. Finding 5 (mapper imports the `registry` package, and so the
  gateways) is not a contract yet: it would break today, and phase 3 fixes it. Listed as known debt with finding 6.

## Corrections

- C1 Full `pytest -n 8`: 2132 passed, 5 skipped, 1 collection error in `tests/unit/test_openapi_spec.py`, which also
  fails on `main` @ cc7a2f2 (it imports the removed `controller.epp_session_authenticator`). Not caused by this
  branch, filed as #124.
