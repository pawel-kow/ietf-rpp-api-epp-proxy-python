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

- Placeholders `{random_name}`, `{random_id_10}` and `{test_start}` are substituted
  per run so tests are idempotent against a shared registry.
- Response body comparison is **subset + case-insensitive**
  (`recusive_compare_existing`) and lists match unordered, because EPP servers may
  uppercase domain/host names and reorder list entries (see
  [RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md)).
- `fields`/`headers` support condition dicts (`not_null`,
  `datetime_format_utc_and_delta`, …) via `evaluate_condition`.

To add a case, drop a new JSON file in the appropriate group dir. No Python changes
are needed. Add `"skip": "reason"` at the top level to skip one.

## Status codes and the spec

- **The oracle for HTTP status codes** is §7 **Table 1** (the normative
  EPP-code→HTTP-status mapping) of the RPP draft in
  `.spec/draft-ietf-rpp-core.clean.txt`. That is how the `2303→404` gap in
  `domains_Update` was found: the handler hardcoded 400 for all EPP errors while
  `domains_Delete` already had the correct `OBJECT_DOES_NOT_EXIST→404` branch.
  `.spec/` is local only: the `*.spec` pattern in `.gitignore` also matches it.
- **Caveat:** §7's prose (the sentence before the table) has 2302/2303 **swapped**
  relative to Table 1. Trust the table (2303→404, 2302→409), which also matches the
  backend's `2303 = "Object does not exist"`.
- **Known spec deviation:** auth failures return **401** here (enforced by
  Connexion's HTTP Basic scheme before the controller runs), whereas §7 maps auth to
  **403**. All existing tests assert 401. Stay consistent unless deliberately
  changing the auth model.
- **Pin the EPP result code.** For error cases, assert the `RPP-code` response
  header (exact string, e.g. `"2303"`) in addition to the HTTP status.

## Probing the backend

To discover real statuses and codes quickly, drop a throwaway JSON in a temp group
dir with a deliberately wrong expected status, run `pytest -k <group>`, and read the
captured `Received response` / `Test case:` line. The runner prints the actual
status, headers including `rpp-code`, and body on failure. Delete the probe
afterwards.

## Isolating cases

Isolate one update facet per file (authInfo-only, hostObj add/remove,
contacts+registrant, …). `domains_Create` and `domains_Update` build their success
body from a follow-up EPP **Info** call, so a passing update test also transitively
exercises Info and `domain_to_rpp`.
