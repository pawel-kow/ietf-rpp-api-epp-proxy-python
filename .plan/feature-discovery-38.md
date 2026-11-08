# feature/discovery-38: Discovery document (#38)

## Tasks

- [x] Plan approved by orchestrator
- [x] Red tests: mapper unit test, wire tests (module-scoped app), config test
- [x] `Discovery` model, `discovery.model_to_rpp` mapper (validates against `discovery.read`)
- [x] `controller/discovery.py` `discovery_read`, config keys in `config.yaml` and `Config`
- [x] Drop `/.well-known/rpp` from the 501 case in `tests/unit/test_rpp_wire.py`
- [x] Docs: architecture.project.md (Configuration, lifecycle), testing.project.md if needed
- [~] Full `pytest` at repo root on the reported commit

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

- Q1: discovery does not touch EPP (anonymous request must not open a backend connection). Wire test uses an EPP client factory that fails if called; asserts no session or login.
- Q2: missing required config answers 500 (02400, COMMAND_FAILED) with a fixed detail naming no keys or values; the log gets a warning naming the missing keys. No startup failure. Values set in `config.yaml`. Base URL is never derived from the `Host` header.
- Q3: one constant "1.0". The proxy has no media type `version` handling and does not enforce core §12's 406: report it.
- Q4: no `Cache-Control`; one line in the spec-issues "Discovery" entry.
- Q5: stay on main, no stacking; `message` not listed (`/messages` is 501 on main). Quote core/json and data-objects §17.2 in the spec entry. File an issue (`severity:low`, `area:not-implemented`) to add `message` after #97.
- Q6: spec-issues line on the json §5.2.1 idnLgr example lacking `url` and `default`.
- Spec entry also: `extensions` omitted (no RPP extension id for secDNS), `profiles` omitted (`GET /profiles/{name}` is 501, but the proxy follows the EPP Compatibility Profile: should the draft name it for discovery?).
- Settings reach the handler through `create_app(authenticator, discovery_settings=None)` (flask app config), composition root passes `config`; tests pass a plain test-double settings object.
- Missing `RPP-Cltrid`: the OpenAPI declares it required, so the answer is a 400 Problem Detail; tested.

## Open questions

See the Plan report.

## Review of PR #100 at 9167ce8: decisions

- Shape check replaces truthiness (`invalid_settings` in the mapper): tlds non-empty list of non-empty strings, environment non-empty strings, base URL absolute https with host. Failure takes the fixed 500 (02400), log names keys only.
- `profiles` is advertised as the constant `urn:ietf:params:rpp:profile:epp-compatibility` (core §12.4, json §8.7.1, data-objects §19.13). `GET /profiles/{name}` stays 501. `links` omitted (SHOULD only).
- Draft case `draft_discovery/test1-read.json` with the configured values. `datetime` is checked as not empty there, because the runner's UTC helper expects fractional seconds. The unit tests check the format and the time.
- Mutants killed (PYTHONDONTWRITEBYTECODE=1): run.py without config, local clock under TZ=Asia/Tokyo, constant datetime, `@rpp_operation` removed, log naming all keys, 500 title.
- Spec entry reworded (items 6, 7), #41 cited (item 8), config.yaml placeholders (item 9). Issue for the 405 headers filed.

## Round 2 decisions

- Base URL: also no userinfo, query, fragment, backslash, whitespace, control characters or malformed `%`; port read inside the `try`. Strings: no padding, no control characters. TLDs: no whitespace at all.
- The profile is defined in data-objects §2.8; §19.13 only creates the registry. Spec entry and `PROFILES` comment corrected; profile error tied to #41.

## Round 3 decisions

- The base URL must also fullmatch the RFC 3986 character set (no `?`, `#`), so non-ASCII, `<>"{}|^`, backtick, zero-width and bidi characters are refused. Legitimate URLs and TLDs have a positive test.
