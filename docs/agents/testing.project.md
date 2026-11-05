# Testing: project specifics

Generic rules are in [testing.md](testing.md).

## Commands

Run from the repository root. `pyproject.toml` sets `pythonpath=src` and
`testpaths=tests`.

```bash
pytest                                                  # all tests
pytest tests/integration/test_from_file_definition.py   # the data-driven integration suite
pytest -k domain_update                                 # single test group by substring
pytest "tests/integration/test_from_file_definition.py::test_from_file_definition[domain_update-test1-simple_update]"  # one case by id
```

## Backend

Integration tests require a **backend EPP test server**. They do not use test
doubles: they exercise the full RPP→EPP→RPP round trip against a live registry.

Its host and port come from `config.yaml` (`rpp_epp_host`/`rpp_epp_port`) via
`new_epp_client` in [src/run.py](../../src/run.py). In the
devcontainer that is the `epp-server-docker-epp-server-1` container on port `700`,
reached over the shared `epp-server-docker_epp_net` docker network (attached via
`postStartCommand` in
[.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json)).

Auth uses HTTP Basic, and the username and password are passed straight through as
the EPP `clID`/`pw` login credentials.

The backend hangs on a repeated clTRID, so every EPP command needs a new one. It drops
addresses given when creating an external host, so tests of addresses at create use an
internal host, which needs its domain to exist first. Its other host defects are
#49, #50, #51, #52 and #54. It rejects non-ASCII contact data, also in `postalInfo
type="loc"` (#55), so non-ASCII localizations are tested only in unit tests.

## Tests without the backend

Unit tests in `tests/unit/` inject test doubles through constructors:

- `EPPClient(transport, username, password)` takes a fake transport.
- `EppSessionAuthenticator(client_factory)` takes a factory returning a fake client,
  such as [FakeEppClient](../../tests/helper/fake_epp_client.py).
- `create_app(authenticator)` builds a full app around that authenticator, so a
  handler can be tested through `test_client()` without a registry. See
  [test_app_injection.py](../../tests/unit/test_app_injection.py).

## Test data format

[tests/integration/test_from_file_definition.py](../../tests/integration/test_from_file_definition.py)
auto-discovers every `*.json` under `tests/integration/test_case_data/<group>/` and
parametrizes one test per file. Each file is a `steps` sequence (e.g. create →
update → verify) run against a Flask test client.

- Placeholders `{random_name}`, `{random_id_10}`, `{test_start}` (start of the case)
  and `{unique_cltrid}` (new value per occurrence) keep tests idempotent against a
  shared registry. The backend requires contact ids to start with `FO-`.
- Every step asserts the headers of core §6.2: `RPP-Svtrid`, a 5-digit `RPP-Code`, and
  `RPP-Cltrid` echoed.
- Response body comparison is **subset + case-insensitive**
  (`recusive_compare_existing`) and lists match unordered, because EPP servers may
  uppercase domain/host names and reorder list entries (see
  [RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md)).
- `fields`/`headers` support condition dicts (`not_null`,
  `datetime_format_utc_and_delta`, …) via `evaluate_condition`. `fields` keys are dotted
  paths, for example `provMetadata.crDate`.
- `draft_domain/`, `draft_contact/`, `draft_host/` and `draft_patch/` hold the examples
  of the JSON draft (§8.1, §8.2, §8.3, §5.3.1). Examples for operations not implemented yet have the
  expected result written down and `"skip": "#<issue>"`.

To add a case, drop a new JSON file in the appropriate group dir. No Python changes
are needed. Add `"skip": "reason"` at the top level to skip one.

## Status codes and the spec

- **The oracle for HTTP status codes** is §18.1 **Tables 9 and 10** of the RPP draft
  in `.spec/draft-ietf-rpp-core.clean.txt`.
- **Pin the RPP result code.** For error cases, assert the `RPP-Code` response
  header (exact string, e.g. `"02303"`) in addition to the HTTP status.

## Probing the backend

To discover real statuses and codes quickly, drop a throwaway JSON in a temp group
dir with a deliberately wrong expected status, run `pytest -k <group>`, and read the
captured `Received response` / `Test case:` line. The runner prints the actual
status, headers including `rpp-code`, and body on failure. Delete the probe
afterwards.

## Isolating cases

Isolate one update facet per file (authInfo-only, hostObj add/remove,
contacts+registrant, …). `domainNames_create` and `domainNames_updatePartial` build their
success body from a follow-up EPP **Info** call, so a passing update test also transitively
exercises Info and `domain_to_rpp`.
