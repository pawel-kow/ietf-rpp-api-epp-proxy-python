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
devcontainer that is the `epp-server-docker-epp-server-1` container on TLS port `743`,
reached over the shared `epp-server-docker_epp_net` docker network (attached via
`postStartCommand` in
[.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json)). Its certificate
is self-signed and does not name that host, so `config.yaml` sets
`rpp_epp_tls_insecure_skip_verify`.

Auth uses HTTP Basic, and the username and password are passed straight through as
the EPP `clID`/`pw` login credentials. The backend has two registrars, `foo` and `baz`
(contact prefixes `FO-` and `BZ-`), and transfer cases set `Authorization` per step.

The backend refuses a repeated clTRID with `2400`, also across sessions, so every EPP command
needs a new one. It drops addresses given when creating an external host, so tests of addresses
at create use an internal host, which needs its domain to exist first. Its other host defects are
#49, #50 and #54. A contact check of an id outside 3 to 16 characters answers available (pawel-kow/epp#24). Info returns no `domain:upID` or `domain:upDate` (#61), so reading `upClientId`
is tested only in unit tests. It refuses the secDNS key data interface with `2306`, and a digest it
already holds even under another keyTag (pawel-kow/epp#20). It stores `domain:hostAttr` as a host
object, so a domain created with glue reads back with `nameservers`. Removing a host from a domain that does not have it succeeds, so "no element matches" is tested with `replace` and `match`, which reads the domain first.

A pending transfer auto-approves after 5 minutes by cron, so a case cannot wait for
`serverApproved`. Info does not show `pendingTransfer` (#64), a completed transfer cannot be
queried (#65), and cancel with nothing pending is `2201` (#66), so its 409 is tested only in
unit tests. `acID` and `acDate` after cancel and reject are not asserted (#67).

## Tests without the backend

Unit tests in `tests/unit/` inject test doubles through constructors:

- `EPPClient(transport, username, password)` takes a fake transport.
- `EppSessionAuthenticator(client_factory)` takes a factory returning a fake client,
  such as [FakeEppClient](../../tests/helper/fake_epp_client.py).
- `create_app(authenticator)` builds a full app around that authenticator, so a
  handler can be tested through `test_client()` without a registry. See
  [test_app_injection.py](../../tests/unit/test_app_injection.py).
- `TCPClient(host, port, tls_context)` connects to a
  [LoopbackEppServer](../../tests/helper/loopback_epp_server.py). Its certificate is
  generated per test session with the `openssl` CLI, so no key is in the repository.

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
  (`recusive_compare_existing`) and lists match unordered, each expected element pairing
  with an actual element of its own, because EPP servers may
  uppercase domain/host names and reorder list entries (see
  [RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md)).
- A step's `response` can be `{"any_of": [...]}`, a list of responses of which one must match,
  for behaviour the protocol leaves to the server. A create that may be refused, or may keep
  the data in another form, lists each outcome, see `domain_create/test16` to `test18`.
- `fields`/`headers` support condition dicts (`not_null`,
  `datetime_format_utc_and_delta`, …) via `evaluate_condition`. `fields` keys are dotted
  paths, for example `provMetadata.crDate`.
- `draft_domain/`, `draft_contact/`, `draft_host/`, `draft_patch/` and `draft_discovery/` hold the examples
  of the JSON draft (§8.1, §8.2, §8.3, §5.3.1, §8.7.1; the discovery one has the configured values). Examples for operations not implemented yet have the
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
exercises Info and `domains.model_to_rpp`.
