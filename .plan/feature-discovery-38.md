# feature/discovery-38: Discovery document (#38)

## Tasks

- [~] Plan approved by orchestrator
- [ ] Red tests: mapper unit test, wire tests (module-scoped app), config test
- [ ] `Discovery` model, `discovery.model_to_rpp` mapper (validates against `discovery.read`)
- [ ] `controller/discovery.py` `discovery_read`, config keys in `config.yaml` and `Config`
- [ ] Drop `/.well-known/rpp` from the 501 case in `tests/unit/test_rpp_wire.py`
- [ ] Docs: architecture.project.md (Configuration, lifecycle), testing.project.md if needed
- [ ] Full `pytest` at repo root on the reported commit

## Findings

- OpenAPI already has `discovery_read` with `security: - {}` (no auth), schema `gen.discovery.read`.
  Required: `@type`, `versions` (1+), `environment` (name, status), `tlds` (1+), `objects` (1+), `datetime`.
  Optional: `extensions`, `profiles`, `links`, `idnLgr`, `notices`.
- Core §11: endpoint MUST be accessible with GET without authentication, 200 on success.
  data-objects §17.3.1: MUST be available without authentication.
- `datetime`: UTC with `Z`, no offset (json §6.10, data-objects §17.2).
- `versions[].version`: Semantic Versioning (json §6.2.13.1).
- `objects` values: object identifiers of the Data Object Registry (`domainName`, `host`, `contact` in the examples).
- No caching rule for the discovery document in core or json (only RPP-Authorization MUST NOT be cached).
- The EPP greeting holds `svID`, `svDate` and `svcMenu` (objURI, extURI). It has no TLDs, no public URL.
  `EPPClient` reads the greeting only inside `connect()`, which logs in. Discovery has no credentials.
- No draft example marked `"skip": "#38"` exists in `tests/` (grep).

## Decisions

(none yet)

## Open questions

See the Plan report.
