# Plan: enforce the module boundaries (#120, phase 1)

Branch `refactor/120-enforce-boundaries`. Phase 1 of #120: write the contracts into `architecture.project.md` and
check them with `import-linter`. No code in `src/` changes.

## Tasks

- [~] T1 `requirements-dev.txt` (`-r requirements.txt` + `import-linter`), installed in `.venv`
- [ ] T2 `[tool.importlinter]` in `pyproject.toml`: one contract per rule, against today's package names
- [ ] T3 `architecture.project.md`: target tree, dependency rules, "must never know", today → target mapping, the
      check; known debt for every `ignore_imports`
- [ ] T4 `process.project.md`: setup with `requirements-dev.txt`, `lint-imports` in "Checks before done"
- [ ] T5 `lint-imports` and full `pytest -n 8` green; draft PR

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
