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
`rpp_epp_tls_insecure_skip_verify`. Where the backend has another name, put it in an untracked
`config.local.yaml` (`rpp_epp_host: epp-server`): its top-level keys replace those of `config.yaml`.

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

The message queue is shared per registrar, and other cases add to it (every transfer request queues a message for the
losing registrar), so `message/` cases assert only the shape of the head and use `any_of` where the queue may be empty.
To ack a real head, a case first requests a transfer, so the queue of `foo` is not empty, and captures `0.id` of
`GET /messages` (`message/test6`). The backend returns the id of the acknowledged message in the `msgQ` of an ack reply.

A contact `chg` of a `postalInfo` form replaces it: the address members not sent again (`sp`, `pc`) are wiped, also when
only `name` or `org` is sent, so the proxy sends every changed form complete (pawel-kow/epp#22). A `chg` of a form the contact does not have
is ignored although the reply is 1000 (pawel-kow/epp#23), so the proxy answers 500 (`02400`) for it (`contact_update/test33` and `test34`), and the cases that change a localization change an existing one (`test8`). Removing a status the contact does not have succeeds, so `test6` and `test19` end on a direct `remove` of an absent label that answers 200.
An empty `org`, `voice` or `fax` clears it and reads back as an empty element. Contact cases prove absence with a PATCH
`remove` that answers 422 (`02308`) because the property is gone, after the same removal answered 200 on a twin contact.

A pending transfer auto-approves after 5 minutes by cron, so a case cannot wait for
`serverApproved`. The domain Info returns no status reason, so a domain PUT with a `reason` is a remove and add each time, and a contact PUT with one is too (the contact Info repeats the label, `contact_update/test7` proves only that the backend accepts it). A registrar that is not
the sponsor gets `2201` from the Info itself, so the refusal of a change of nothing by a non-sponsor is tested only in unit tests
(`domain_update/test30` and `test31` pass on the backend's `2201`). A domain PUT without `registrant` removes it, the backend answers 200. Absence of the registrant is shown
by a PATCH that removes it and `/status`, which forces the read path: 422 `02308` without a registrant, 200 with one (`domain_update/test32`). A domain create with `hostAttr` and no address is refused with `2003`, so the host
objects are created with `nameservers` and a PUT with `ns` records follows (`domain_update/test29`).

Info does not show `pendingTransfer` (#64), a completed transfer cannot be
queried (#65), and cancel with nothing pending is `2201` (#66), so its 409 is tested only in
unit tests. `acID` and `acDate` after cancel and reject are not asserted (#67). Contact transfers behave the same, except that Info does show the sponsor changing, so `contact_transfer` cases read it back.

The IDN tables of the backend are `de` and `es`, and `config.yaml` maps `latn-1.0` to `de` only, so a read with an
unmapped table is tested only in unit tests. It answers 2306, not the 2005 of draft-obispo-epp-idn-04, for a `uname`
that does not match the name. Its IDN tables and the session table come from migrations in EPP-server-docker, which run
only when the database is first created: a database from before them answers `2306 Unknown idn:table` and needs them
applied by hand.

Its RFC 3915 periods are minutes (pawel-kow/EPP-server-docker#5): a domain deleted within 2 minutes of its create is
purged at once, a later delete puts it in `redemptionPeriod`, and a request then holds it in `pendingRestore` for 3
minutes. So a restore case creates its domain and deletes it after `delay_seconds` of 125, see `domain_restore/test12`
and the draft examples. The backend sends no `rgp:upData`. A read of `pendingDelete` would need the 5-minute
redemption period to pass, so it is tested only in unit tests.

The backend refuses a renew period under one year (`2306`), so month periods are 12 or more. A wrong
`expiryDate` is `2306`. A renew without `renewalPeriod` leaves the expiry as it was (pawel-kow/epp#25), so `test2` proves acceptance only.

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
  shared registry. The backend requires contact ids to start with `FO-`. `{ulabel:TEXT}` is the U-label
  `TEXT-<random_id_10>` and `{alabel:TEXT}` its A-label, so an IDN case writes `{alabel:bücher-t24}.example`.
  `{upper:TEXT}` is TEXT in upper case, after the other placeholders in it are replaced. The backend stores host
  names in upper case, so a `match` on a generated host writes `{upper:ns1.u17-{random_name}.net}`.
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
- A step's `capture` maps a name to a dotted field of its response body, where a number picks a list element (`0.id`). Later steps write `{capture:name}`
  in their request or expected response, and `{capture:name+Ny}` for that timestamp N years later. It is how
  a renew sends the exact current `expiryDate`, see `domain_renew/test10`.
- A step's `delay_seconds` waits that long before its request, for a registry period that must pass first. Each
  wait adds to the run, so a case waits at most once, see `domain_restore/`.
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

Absence cannot be asserted, because the body comparison is a subset. A case shows that something was removed with a
`replace` with `match` on it, which reads the domain and answers 422 `02308`. The same `match`, in the form the
registry stores (`{upper:...}`, as a match is exact), must first answer 200 before the removal, or the 422 proves
nothing (see `domain_update/test17`).

A case creates the contacts, hosts and domains it uses, in its first steps, and relies on nothing seeded in the
backend. `{random_name}` and `{random_id_10}` are the same for every case of a run, so each case adds its own part:
contacts are `FO-{random_id_10}` plus a suffix of the case (`ua1`, at most 16 characters in all), hosts are external
`nsN.<case>-{random_name}.net`, which need their own `ns` record at create. `domain_create/test7` creates the domain
it then finds taken.

Isolate one update facet per file (authInfo-only, hostObj add/remove,
contacts+registrant, …). `domainNames_create`, `domainNames_updatePartial` and `domainNames_update` build their
success body from a follow-up EPP **Info** call, so a passing update test also transitively
exercises Info and `domains.model_to_rpp`.
