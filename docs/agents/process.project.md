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
pip install -r requirements.txt

# Run the server (must run from src/: the app resolves openapi.yaml and config.yaml relative to CWD)
cd src && uvicorn run:app        # Swagger UI at http://127.0.0.1:8000/ui/

# Docker
docker build . -f ./.docker/Dockerfile -t pawelk/rpp_server_epp_proxy
docker run --rm -p 8000:8091 pawelk/rpp_server_epp_proxy
```

## Checks before done

There is no CI in this repository. The only check is the full `pytest -n 8` run from
the repository root, which needs the live backend. See
[testing.project.md](testing.project.md).

## Issue labels

Use `bug` for defects, plus one `severity:*` label (`critical`, `high`, `medium`,
`low`) and one `area:*` label (`functional`, `spec-compliance`, `not-implemented`,
`tech-debt`, `refactoring`, `performance`, `build`, `chores`).
