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

## Tasks
- [~] Plan approved
- [ ] Remove `backend_parts` (RegisteredExtension, registry `backend_parts()`, seven registers)
- [ ] PARTS in `registry_adapter/{rri,sqlite}/extensions/__init__.py`
- [ ] `registry_setup`: backend catalogue lookup, refusal, `main` wiring
- [ ] Tests (test_registration, test_planets_wire, helper/profiles, refused_configs, test_extension_isolation)
- [ ] Docs: architecture.project.md, registered_extension docstring, pyproject comment
- [ ] Checks: lint-imports, unit, smoke, MTEST reachability
- [ ] Draft PR

## Findings
- `backend_parts` users: main.py:89,97, registry_setup.py:15, extension_registry.py, 7 registers, tests (4 files),
  architecture.project.md:585. No mention in config/, deploy/, docs/demo.
- tests/refused_configs register test-only data extensions with a SQLite part: they need an entry in the SQLite PARTS.
