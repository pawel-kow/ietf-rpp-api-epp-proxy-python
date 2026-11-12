# Testing: project specifics

Generic rules are in [testing.md](testing.md).

## Commands

Run from the repository root. `pyproject.toml` sets `pythonpath=src` and
`testpaths=tests`.

```bash
pytest -n 8                                             # all tests, in 8 workers (pytest-xdist)
pytest                                                  # all tests, one at a time
pytest tests/integration/test_from_file_definition.py   # the data-driven integration suite
pytest -k domain_update                                 # single test group by substring
pytest "tests/integration/test_from_file_definition.py::test_from_file_definition[domain_update-test1-simple_update]"  # one case by id
```

Run the full suite with `-n 8`, which takes about 5.5 minutes on 4 cores. The unit tests are bound by CPU,
mostly building an app per test from `openapi.yaml`, so more workers than cores do not speed them up, and the backend refuses logins under about
16 concurrent sessions (pawel-kow/EPP-server-docker#7), so 8 is the most it takes. Every worker makes its own
`{random_name}`, so cases in different workers do not collide.

## Backend

Integration tests require a **backend EPP test server**. They do not use test
doubles: they exercise the full RPP→EPP→RPP round trip against a live registry.

Its host and port come from `config.yaml` (`rpp_epp_host`/`rpp_epp_port`) via
`new_epp_client` in [src/main.py](../../src/main.py). The backend is a docker compose project (today `epptest`),
and `config.yaml` names its EPP server by the compose service name, `epp-server`, on TLS port `743`. That name
resolves on the project's network, `<project>_epp_net` (today `epptest_epp_net`), which the devcontainer has to
join: `postStartCommand` in [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json) no longer does it
(#111), so attach it by hand: `docker network connect epptest_epp_net <container>`, where `<container>` is the
devcontainer's id (`cat /etc/hostname` inside it). Without it every
integration case fails with 401 (`02200`). Its certificate is self-signed and does not name that host, so
`config.yaml` sets `rpp_epp_tls_insecure_skip_verify`. Where the backend has another name, put it in an untracked
`config.local.yaml` (`rpp_epp_host: <name>`): its top-level keys replace those of `config.yaml`.

Auth uses HTTP Basic, and the username and password are passed straight through as
the EPP `clID`/`pw` login credentials. The backend has two registrars, the slots `a` and `b` of the cases, whose
credentials and contact id prefixes are in `.env` (see [Test environments](#test-environments)), and transfer cases
set `Authorization` per step.

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

## Test environments

A test environment is one backend server the integration suite runs against, chosen with `RPP_TEST_ENV` (default
`epp-docker`) and described in `tests/integration/environments/<name>.yaml`: the config file of the app under test
(`tests/conftest.py` sets `RPP_CONFIG_FILE` from it before any test module composes the app), the `BackendProfile` it
is composed with, the most workers it allows, the requests a minute per registrar (`rpp_requests_per_minute`, paced
by [pacer.py](../../tests/helper/pacer.py)), the registrars, and its `facts`. A run with more workers than the
environment allows does not start.

The registrars name the variables that hold their credentials, the prefix of the handles they create, and on RRI
their General Request and Abuse contacts. The runner reads them from the process environment or from `.env` in the
repository root (python-dotenv; the proxy never reads it). [.env.example](../../.env.example) names them all. A
missing variable stops the run with its name, so no case logs in with an empty one. The runner puts a credential
into the `Authorization` header when it sends the request, never into the case, so a failure report cannot print it.

| Placeholder | Is |
|---|---|
| `{auth:a}`, `{auth:b}` | HTTP Basic of registrar `a` or `b` |
| `{auth:a:wrong_password}`, `{auth:unknown_user}` | a wrong password of `a`, a user the backend does not know. Refused where `env.failed_logins_lock` is true |
| `{handle:a:SUFFIX}` | `<prefix of a>{random_id_10}SUFFIX`, a contact id `a` may create |
| `{regacc:a}` | the sponsor id of `a`: its login on EPP, the RegAccId of its login on RRI |
| `{gen_req:a}`, `{abuse:a}` | the REQUEST contacts of `a` (RRI only) |
| `{tld}` | the TLD the environment registers under (`env.tld`) |
| `{env:FACT}` | a fact of the environment, such as `{env:environment_name}` |
| `{lower:TEXT}` | TEXT in lower case, after the placeholders in it, for an id sent in another case than stored |

### DENIC MTEST

`RPP_TEST_ENV=rri-mtest pytest -n 4 tests/integration` runs the suite against DENIC's RRI test environment through
[config.rri-mtest.yaml](../../config.rri-mtest.yaml). It needs the IPv4 address of the machine on the allowlist of
both RegAccs (the devcontainer goes out with the host's address), and the `TEST_RRI_*` variables in `.env`: the two
logins, their passwords, the prefix of the handles the cases create (it starts with the RegAccId), and a REQUEST
contact of each RegAcc for the General Request and Abuse roles, created beforehand outside the suite (RPP cannot
create one yet, gap Q2). Of the run's limits: 4 sessions and 100 RRI requests a minute per RegAcc, so at most 4
workers and 25 RPP requests a minute per registrar, paced by the runner. 10 failed LOGINs lock a user for an hour, so
no case with wrong credentials runs there (`env.failed_logins_lock`). The RGP is a day, so restores are tested in unit
tests only. MTEST keeps what the cases create: they delete their domains, and the contacts stay (RRI cannot delete
one), which the random part of the handle keeps apart. Every case runs on both backends unless it needs a function one of them lacks, which its `when`
names: host objects, client statuses, `ds` records, registration periods, renew, transfers, restore within the run,
contact delete, a contact's authInfo, a localization, a fax, a region, a changeable contact name, a person's name
on an organisation, a readable domain authInfo, the admin, tech and billing roles, or wrong credentials. Where the
backends differ in what a case sends or expects, the case selects by the fact: a contact has a phone and a full
address on both (RRI requires them); a domain gets an `a` record (`profile.domain_dns_required`) and a registrant,
created in a first step of its own (`profile.registrant_required`); the roles are `generalRequest` and `abuse` where
the backend has no `admin`; `expiryDate`, the provisioning metadata RRI does not show (`profile.metadata`), a
domain's authInfo and its `ok` status right after its create (`env.domain_active_at_create`; an MTEST domain is
`pendingCreate`, and `failed` with name servers that do not serve it) are left out where they do not apply. Passwords
are of the characters an RRI AuthInfo takes. Where a function exists on one backend only, a counterpart case covers
the other (`domain_update/test35` to `test37`, `domain_lifecycle/`).

Behaviour of MTEST the cases depend on: every reply carries info `13000000011`; a new domain is `pendingCreate`, or
`failed` when its name servers do not pass the predelegation check (the create still succeeds); an MX exchange must
resolve; CREATE-AUTHINFO1 without an expiry gives one two days ahead (#134); handles come back in upper case and IPv6
addresses uncompressed; the IDN repertoire holds `ñ`, which the `de` table of the EPP test server does not
(`env.lgr_without_enye`); a read reusing a client transaction id is not refused, only a write would be
(`env.cltrid_reuse_refused`); an `lgr` on an ASCII name is not refused, RRI takes no LGR (`env.lgr_on_ascii_refused`);
clearing a contact's name or email is refused by RRI with 422 `02306`, where the EPP adapter refuses it with 501
(`env.contact_removal_refused_by_registry`). [config.rri-mtest.yaml](../../config.rri-mtest.yaml) offers `latn-1.0` as the LGR, which
the descriptor states as `lgrs`, as `epp-docker.yaml` does for `config.yaml`.

## Selectors

A case file says which backends a case, a step or an expected value is for (implemented in
[selectors.py](../../tests/helper/selectors.py)). A selector is an object whose keys name facts and which holds when
every key holds. `profile.<fact>` is a field of the `BackendProfile` of the app under test, `env.<fact>` one of the
environment's `facts`. A value holds when the fact equals it; `{"contains": x}`, `{"min": n}`, `{"max": n}` and
`{"not": v}` test a collection, a number or the opposite. A list of selectors holds when one of them does. There is
no selector on the backend's name: a difference is stated as the fact it comes from, and a fact the profile lacks is
added to it when it is true of the protocol, to the environment when it is true of one server.

| Where | Form | Effect |
|---|---|---|
| A group | `_group.json` in the group directory: `{"when": …}` | every case of the group is skipped where it does not hold |
| A case | `"when"` at the top level | the case is skipped where it does not hold |
| A step | `"when"` in the step | the step is left out. A step with `when` cannot `capture` |
| Any value of a step | `{"select": [{"when": …, "then": …}, …, {"then": …}]}` | the `then` of the first entry that holds; the last entry is the default. An entry `{"omit": true}` instead of `then` leaves the member or list element out |

Selectors are resolved first, then the placeholders, then the captures. A selector key that names no fact, in any
known environment, fails the case at load. A skip names the facts that did not hold. A case whose selectors skip it
in every known environment fails, because it never runs. `any_of` stays for what the protocol leaves to the server,
`select` is for what differs by backend or server, and `"skip": "#<issue>"` for a known defect.

## Tests without the backend

Unit tests in `tests/unit/` inject test doubles through constructors:

- `EPPClient(transport, username, password)` takes a fake transport.
- `EppBackend(epp_client, ns_map, idn_tables=None)` takes a fake client, such as
  [FakeEppClient](../../tests/helper/fake_epp_client.py), and a flow takes that backend. Tests pass
  [EPP_NS_MAP](../../tests/helper/epp_ns_map.py), the namespace map of `config.yaml`, which the XML tests assert;
  the `*_xml` functions take it as `ns_map`, and the domain ones `IdnTables` as `idn_tables`.
- `SessionPool(backend_factory)` takes a factory returning a backend.
  [epp_backends](../../tests/helper/epp_backends.py) turns a factory of fake EPP clients into one, so the test still
  sees the clients.
- `create_app(sessions, profile)` builds a full app around that session pool and a `BackendProfile`
  (`EPP_PROFILE`, or `epp_profile(idn_tables)` for IDNs), so a handler can be tested through `test_client()` without
  a registry. See [test_app_injection.py](../../tests/unit/test_app_injection.py).
- The domain mappers take `profile=EPP_PROFILE`. A test that calls `map_request` directly uses the fixture of
  [epp_app_context](../../tests/helper/epp_app_context.py), from which `map_request` names the backend.
- `RriBackend(FakeRriClient(replies=[...]))` runs the RRI adapter over RRI XML replies
  ([fake_rri_client.py](../../tests/helper/fake_rri_client.py)); the replies recorded from MTEST are in
  `tests/unit/rri_replies/`, with personal data replaced. `rri_backends(factory)` builds an app around them, as
  `epp_backends` does.
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
  shared registry. A contact id is `{handle:a:SUFFIX}`, because the backend requires the prefix of its registrar. `{ulabel:TEXT}` is the U-label
  `TEXT-<random_id_10>` and `{alabel:TEXT}` its A-label, so an IDN case writes `{alabel:bücher-t24}.{tld}`.
  `{upper:TEXT}` is TEXT in upper case, after the other placeholders in it are replaced. The backend stores host
  names in upper case, so a `match` on a generated host writes `{upper:ns1.u17-{random_name}.net}`.
  `{pad:N:TEXT}` is TEXT followed by the digits 0 to 9, repeated, to N characters, for a name or id of an exact
  length that keeps the random part of TEXT: `{pad:63:t3-{random_name}}.{tld}` is a label of 63.
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

`authInfo` is `onDemand`, so a step that expects it in a response asks for it with `?includeElements=authInfo`. A PUT
without it leaves the password alone and does not show it, so a GET that includes it follows to prove the password.

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

## Limits

`limits_domain/`, `limits_contact/` and `limits_host/` probe each limit with the value at it and the value past it.
What the drafts define is the oracle; a limit they leave to the server is expected to be refused with 400 (`02001`,
`02004`, `02005`) or 422 (`02306`), never 500 or 501. A limit that differs by server is a `limit_*` fact of the
environment, and `values_cut_at_column` marks a server that stores a value cut instead of refusing it, where the cases
over a column do not run. The EPP test server cuts strings (pawel-kow/epp#21) and phone extensions (pawel-kow/epp#31),
breaks on a label of 61 to 63 characters under `.example` (pawel-kow/epp#30), and counts nameservers, contacts a role
and host addresses per command, so an update can pass its limits (pawel-kow/epp#29). The limits and their sources are in [backend-limits.yaml](../testing/backend-limits.yaml),
the coverage of every field in [integration-test-review.md](../testing/integration-test-review.md).

## Isolating cases

Absence cannot be asserted, because the body comparison is a subset. A case shows that something was removed with a
`replace` with `match` on it, which reads the domain and answers 422 `02308`. The same `match`, in the form the
registry stores (`{upper:...}`, as a match is exact), must first answer 200 before the removal, or the 422 proves
nothing (see `domain_update/test17`).

A case creates the contacts, hosts and domains it uses, in its first steps, and relies on nothing seeded in the
backend. `{random_name}` and `{random_id_10}` are the same for every case of a run, so each case adds its own part:
contacts are `{handle:a:SUFFIX}` with a suffix of the case (`ua1`, at most 16 characters in all on EPP), hosts are external
`nsN.<case>-{random_name}.net`, which need their own `ns` record at create. `domain_create/test7` creates the domain
it then finds taken.

Isolate one update facet per file (authInfo-only, hostObj add/remove,
contacts+registrant, …). `domainNames_create`, `domainNames_updatePartial` and `domainNames_update` build their
success body from a follow-up EPP **Info** call, so a passing update test also transitively
exercises Info and `domains.model_to_rpp`.
