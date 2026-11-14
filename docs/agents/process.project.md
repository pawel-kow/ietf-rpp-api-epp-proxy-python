# Process: project specifics

Generic rules are in [process.md](process.md).

Ambiguity in an EPP/RPP mapping counts as "in doubt": ask, because a wrong
assumption in a protocol bridge is expensive to unwind.

## Environment

The system `python --version` is 3.9, but the code uses 3.10+ syntax (`str | None`,
`tuple[...]`, `dict[str,str]`). Use the `.venv` interpreter, which is newer.

## Commands

```bash
# Setup
python -m venv .venv && . .venv/bin/activate
pip install -r requirements-dev.txt     # requirements.txt plus the development tools

# Run the server (from src/: config.yaml is read relative to the working directory)
cd src && uvicorn main:app        # Swagger UI at http://127.0.0.1:8000/ui/

# Docker
docker build . -f ./.docker/Dockerfile -t pawelk/rpp_server_epp_proxy
docker run --rm -p 8000:8091 pawelk/rpp_server_epp_proxy
```

## Checks before done

There is no CI in this repository. Run these checks from the repository root, in this order:

1. `PYTHONPATH=src lint-imports`: the module boundaries, see
   [architecture.project.md](architecture.project.md#the-check).
2. The unit tests, `pytest -n 4 tests/unit`.
3. The smoke suite, `pytest -n 4 -m smoke tests/integration` (about 2.5 minutes), which needs the live backends: it
   tests every environment whose credentials are in `.env`. See
   [testing.project.md](testing.project.md#test-data-format). The full run, `pytest -n 4` (about 40 minutes), only
   when the maintainer asks for it.
4. For a change to `registry_adapter/rri/`, `core` or `rpp`: the smoke run includes DENIC MTEST, from a machine on
   the allowlist of both RegAccs, before the PR leaves draft. A coder without such a machine runs
   `RPP_TEST_ENV=epp-docker pytest -n 8 -m smoke tests/integration` and records the MTEST run as pending in the plan.

## Issue labels

Use `bug` for defects, plus one `severity:*` label (`critical`, `high`, `medium`,
`low`) and one `area:*` label (`functional`, `spec-compliance`, `not-implemented`,
`tech-debt`, `refactoring`, `performance`, `build`, `chores`).
