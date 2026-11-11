# Plan: restructure src/ into core, rpp and registry adapters (#120, phases 2-6)

Branch `refactor/120-restructure`, one draft PR for phases 2 to 6 (maintainer). Behaviour does not change: every phase
ends with `PYTHONPATH=src lint-imports` and the full `pytest -n 8`, and is its own commit.

## Tasks

- [~] T0 Move tool (scratchpad): moves modules and rewrites every import in `src/` and `tests/` as an absolute import
      from the defining module; star imports become the names used
- [ ] T1 Phase 2: `eppclient`, `epp_to_model_mapper`, `helpers` → `registry_adapter/{epp,common}`; `ns_map` passed in;
      `commands/not_used/` deleted; contracts renamed
- [ ] T2 Phase 3: `models`, `registry`, `flows` → `core/` per object; explicit imports; `BackendProfile` and the
      refusals → `core/capabilities`
- [ ] T3 Phase 4: `controller` → `rpp/http` + `rpp/handlers`; mappers and schema validator → `rpp/`; session pool →
      `core/session`; `run.py` → `main.py`; `copy_models.sh`, Dockerfile and docs for `uvicorn main:app`
- [ ] T4 Phase 5: `IdnTables` → `epp/`; read-back once (closes #17); settings passed in
- [ ] T5 Phase 6: result envelope for gateway results
- [ ] T6 Docs (`architecture.project.md`, `testing.project.md`, `process.project.md`, README), import-linter contracts
      for the target, final checks, draft PR

## Findings (evidence)

1. 230 modules outside the generated packages; tests import them by module path in 71 test files.
2. Star imports outside `__init__`: `controller/{domains,contacts}.py`, `eppclient/epp_{domains,contacts}.py`,
   `epp_to_model_mapper/{domains,contacts}.py`, `app.py`.
3. `epp_to_model_mapper/commands/helper.py:25` renders with `config.rpp_epp_ns_map`; the XML tests assert the prefixes
   of that map (`domain:`).
4. `RelativeResolver('controller')` resolves an operationId as an attribute of the package, so the handlers package
   keeps re-exporting the handlers.
5. `models/contacts.py:52` defines a second `ErrorResponse`, besides `models/response.py`.

## Decisions

- D1 (maintainer) Phases 2-6 in one draft PR, without acceptance between phases.
- D2 Package `__init__` files are empty, except `rpp/handlers`, whose functions connexion resolves by name (finding 4).
- D3 Imports are absolute.
- D4 `epp/commands/<object>/` keeps today's three layers as three modules: `epp_request.py` (the xsdata request),
      `<object>_xml.py` (render, parse), `<object>_commands.py` (one operation: render → send → parse). Shared reply
      parsing in `epp/commands/shared/`.
- D5 `ns_map` goes into an `EppCodec` built by the composition root, held by `EppBackend` and passed to the commands.
