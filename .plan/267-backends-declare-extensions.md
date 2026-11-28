# 267: backends declare the extensions they implement

Stacked on #266 (`261-rri-split-messages`); the PR targets main and must merge after #266.

## Decisions (maintainer, via orchestrator)
- `backend_parts` is removed from `RegisteredExtension` and from every `register` (planets, planet_atmosphere,
  satellite_orbit, rri, messages, domain_lock, registry_changes). A registration covers the RPP side only.
- Each backend with extensions declares them: `registry_adapter/<backend>/extensions/__init__.py`,
  `PARTS = {extension id: part module path}` (RRI, SQLite). Explicit catalogue, no scanning. Part modules stay.
  Ids are imported from the extensions' core constants if import-linter allows.
- Startup: every extension of `rpp_extensions` must be in the backend's PARTS, else refuse to start (same kind of error
  as `registry_setup.py`). EPP has no package: holds none. main passes PARTS filtered to the registered extensions to
  `load_rri_parts` / `load_extension_parts`; keep the `needing_gateways` check.
- Keep `extension-not-adapter`; check the other contracts.
- Wire contract unchanged. #203 stays separate (note in PR).

## Decisions (orchestrator, plan approval)
- Deviation: PARTS is a plain dict of id string -> part module path; no extension core is imported by the catalogue
  (lazy: a deployment imports only what it configures). A unit test checks each key against the EXTENSION_ID of its
  extension and that every extension of the demo/RRI configs is in the catalogue.
- Test-only extensions add their PARTS entry in the test helper (`register_definitions`), in the process that registers
  them (not monkeypatch: one test starts the server in a subprocess). No test ids in production code.
- #203: note only.

## Results
- lint-imports: 41 kept, 0 broken (no contract changed; only a pyproject comment).
- unit: 3443 passed. smoke: 251 passed, 581 skipped (includes rri-mtest; reachability case passed first).

## Tasks
- [x] Plan approved
- [x] Remove `backend_parts` (RegisteredExtension, registry `backend_parts()`, seven registers)
- [x] PARTS in `registry_adapter/{rri,sqlite}/extensions/__init__.py`
- [x] `registry_setup`: backend catalogue lookup, refusal, `main` wiring
- [x] Tests (test_registration, test_planets_wire, helper/profiles, refused_configs, test_extension_isolation)
- [x] Docs: architecture.project.md, registered_extension docstring, pyproject comment
- [x] Checks: lint-imports, unit, smoke, MTEST reachability
- [~] Draft PR

## Findings
- `backend_parts` users: main.py:89,97, registry_setup.py:15, extension_registry.py, 7 registers, tests (4 files),
  architecture.project.md:585. No mention in config/, deploy/, docs/demo.
- tests/refused_configs register test-only data extensions with a SQLite part: they need an entry in the SQLite PARTS.

- Review rounds 1-2 changed tests only (catalogue restore fixture, environments by glob); the smoke run (251 passed, 581 skipped, incl. MTEST) stands.
