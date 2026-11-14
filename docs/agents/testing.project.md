# Testing: project specifics

Generic rules are in [testing.md](testing.md).

## Commands

Run from the repository root. `pyproject.toml` sets `pythonpath=src` and
`testpaths=tests`.

```bash
pytest -n 4                                             # all tests, in 4 workers (pytest-xdist), every environment
pytest                                                  # all tests, one at a time
RPP_TEST_ENV=epp-docker pytest -n 8                     # the cases of one environment only, the others skipped
pytest tests/integration                                # the data-driven integration suite
pytest -n 4 -m smoke                                    # the smoke suite, in every environment
pytest -k domain_update                                 # single test group by substring, in every environment
pytest -k "rri-mtest and domain_update"                 # single test group in one environment
pytest -k domain_update-test1-simple_update             # one case by <group>-<test_id>
pytest "tests/integration/file_cases.py::epp-docker::domain_update::test1-simple_update"  # one case by id
pytest tests/integration/test_case_data/domain_update/test1-simple_update.json  # one case file, in every environment
```

Each iteration runs the unit tests and the smoke suite ([process.project.md](process.project.md#checks-before-done)),
the full suite only when the maintainer asks for it. Run it with `-n 4`, the most workers DENIC MTEST allows, since a
run tests every environment whose credentials are in `.env`; on both backends it takes about 40 minutes. Against the EPP test server alone (`RPP_TEST_ENV=epp-docker`) `-n 8` takes about 15
minutes on 4 cores, most of it the cases that wait for the periods of the EPP test server (`domain_lifecycle/test8`
waits about 14 minutes). The unit tests are bound by CPU,
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

A pending transfer is approved by the server after 5 minutes (`domain_transfer/test13`, `contact_transfer/test18`).
The domain Info returns no status reason, so a domain PUT with a `reason` is a remove and add each time, and a contact PUT with one is too (the contact Info repeats the label, `contact_update/test7` proves only that the backend accepts it). A registrar that is not
the sponsor gets `2201` from the Info itself, so the refusal of a change of nothing by a non-sponsor is tested only in unit tests
(`domain_update/test30` and `test31` pass on the backend's `2201`). A domain PUT without `registrant` removes it, the backend answers 200. Absence of the registrant is shown
by a PATCH that removes it and `/status`, which forces the read path: 422 `02308` without a registrant, 200 with one (`domain_update/test32`). A domain create with `hostAttr` and no address is refused with `2003` (pawel-kow/epp#33), so the host
objects are created with `nameservers` and a PUT with `ns` records follows (`domain_update/test29`).

Info does not show `pendingTransfer` (#64), a completed transfer cannot be
queried (#65), and cancel with nothing pending is `2201` (#66), so its 409 is tested only in
unit tests. `acID` and `acDate` after cancel and reject are not asserted (#67). Contact transfers behave the same, except that Info does show the sponsor changing, so `contact_transfer` cases read it back.

The IDN tables of the backend are `de` and `es`, and `config.yaml` maps `latn-1.0` to `de` only, so a read with an
unmapped table is tested only in unit tests. It answers 2306, not the 2005 of draft-obispo-epp-idn-04, for a `uname`
that does not match the name. Its IDN tables and the session table come from migrations in EPP-server-docker, which run
only when the database is first created: a database from before them answers `2306 Unknown idn:table` and needs them
applied by hand.

Its RFC 3915 periods are minutes (pawel-kow/EPP-server-docker#5), stated as the environment's periods (see
[Waiting for a period](#waiting-for-a-period)): a domain deleted within its add grace period is purged at once, a
later delete puts it in `redemptionPeriod`, and a request then holds it in `pendingRestore`. So a restore case
deletes its domain after `wait` for `domainName.processes.create.add_grace_period`, see `domain_restore/test12`. The
backend sends no `rgp:upData`.

The backend refuses a renew period under one year (`2306`), so month periods are 12 or more. A wrong
`expiryDate` is `2306`. A renew without `renewalPeriod` leaves the expiry as it was (pawel-kow/epp#25), so `test2` proves acceptance only.

## Test environments

A test environment is one backend server the integration suite runs against, described in
`tests/integration/environments/<name>.yaml`. A run tests every environment, each with an app of its own composed
from its config by `main.compose`, its credentials and its pacer, or only those `RPP_TEST_ENV` names
(comma-separated); the cases of the others are skipped as not selected, and those of an environment whose
credentials are missing from `.env` are skipped with the variables it needs. The unit tests compose the app of the
first environment `RPP_TEST_ENV` names, default `epp-docker` (`tests/conftest.py` sets `RPP_CONFIG_FILE` from it
before any test module imports `main`). The descriptor holds the config file of the app under test, the most workers it
allows, the requests a minute per registrar (`rpp_requests_per_minute`, paced
by [pacer.py](../../tests/helper/pacer.py)), the registrars, a user the backend does not know, and its `facts`. The
`BackendProfile`, the TLD, the environment name and the LGRs are read from that config, as the app reads them, and not
repeated. A run with more workers than an environment it tests allows does not start.

The registrars name the variables that hold their credentials, the prefix of the handles they create, and on RRI
their General Request and Abuse contacts. The runner reads them from the process environment or from `.env` in the
repository root (python-dotenv; the proxy never reads it). [.env.example](../../.env.example) names them all. A
missing variable stops the run with its name, so no case logs in with an empty one. The runner puts a credential
into the `Authorization` header when it sends the request, never into the case, so a failure report cannot print it.

| Placeholder | Is |
|---|---|
| `{auth:a}`, `{auth:b}` | HTTP Basic of registrar `a` or `b` |
| `{auth:unknown_user}` | a user the backend does not know. No case logs in to a test account with a wrong password, which could lock it |
| `{handle:a:SUFFIX}` | `<prefix of a>{random_id_10}SUFFIX`, a contact id `a` may create |
| `{regacc:a}` | the sponsor id of `a`: its login on EPP, the RegAccId of its login on RRI |
| `{gen_req:a}`, `{abuse:a}` | the REQUEST contacts of `a` (RRI only) |
| `{tld}` | the TLD the environment registers under, the first of `rpp_tlds` of its config |
| `{env:environment_name}` | `rpp_environment_name` of its config |
| `{env:<path>}` | a fact of the environment. A list fact is a whole value only, and the response may hold any of its entries: `"label": "{env:domainName.processes.create.success_status}"` |
| `{lower:TEXT}` | TEXT in lower case, after the placeholders in it, for an id sent in another case than stored |

### DENIC MTEST

`RPP_TEST_ENV=rri-mtest pytest -n 4 tests/integration` runs the suite against DENIC's RRI test environment alone through
[config.rri-mtest.yaml](../../config.rri-mtest.yaml). It needs the IPv4 address of the machine on the allowlist of
both RegAccs (the devcontainer goes out with the host's address), and the `TEST_RRI_*` variables in `.env`: the two
logins, their passwords, the prefix of the handles the cases create (it starts with the RegAccId), and a REQUEST
contact of each RegAcc for the General Request and Abuse roles, created beforehand outside the suite (RPP cannot
create one yet, gap Q2). Of the run's limits: 4 sessions and 100 RRI requests a minute per RegAcc, so at most 4
workers and 25 RPP requests a minute per registrar, paced by the runner. A session dropped without LOGOUT counts
until its idle timeout of 5 minutes, and a LOGIN past the limit is refused with `73100000005`, so each worker logs its
sessions out when the run ends (`pytest_sessionfinish`, `SessionPool.close`); a killed run cannot, and the next run
within 5 minutes may be refused. Two runs at once (a terminal and VS Code) share the 4 sessions. 10 failed LOGINs lock a user for an hour,
so the failed logins are of an unknown user. A RESTORE is one step and needs no wait; the RGP and the purge after it
take up to two days, which a run waits for only with `RPP_TEST_MAX_WAIT` of `P2DT6H` or more. MTEST keeps what the cases create: they delete their domains, and the contacts stay (RRI cannot delete
one), which the random part of the handle keeps apart. Every case runs on both backends unless it needs a function one of them lacks, which its `when`
names: host objects, client statuses, `ds` records, registration periods, renew, transfers, a restore report, a period longer than the run waits,
contact delete, a contact's authInfo, a localization, a fax, a region, a changeable contact name, a person's name
on an organisation, a readable domain authInfo, or the admin, tech and billing roles. Where the
backends differ in what a case sends or expects, the case selects by the fact: a contact has a phone and a full
address on both (RRI requires them); a domain gets an `a` record (`profile.domainName.dns.min_count`) and a
registrant, created in a first step of its own (`profile.domainName.registrant.min_count`); the roles are
`generalRequest` and `abuse` where the backend has no `admin`; `expiryDate`, the provisioning metadata RRI does not
show (`profile.domainName.metadata`) and a domain's authInfo are left out where they do not apply; the status a domain
reads with right after its create is one of `env.domainName.processes.create.success_status` (`ok` on the EPP test
server; on MTEST `pendingCreate` while the predelegation check runs, `ok` once it passed). A case gives DNS data that
passes the check (an `a` record DENIC serves itself), unless the check is its subject: name servers that do not serve
the domain make it `inactive` (`env.domainName.processes.create.failed_dns_status`, `domain_create/test43`). Passwords
are of the characters an RRI AuthInfo takes. Where a function exists on one backend only, a counterpart case covers
the other (`domain_update/test35` to `test37`, `domain_lifecycle/`).

Behaviour of MTEST the cases depend on: every reply carries info `13000000011`; a new domain is `pendingCreate`, or
`failed` when its name servers do not pass the predelegation check (the create still succeeds, and the domain reads
back `inactive` with a `due`); an update that keeps or adds such name servers is refused (`53300102912`), so a change
of `ns` or `dnskey` records cannot succeed there and its cases expect the refusal; a DNSKEY must be a valid key, and a
domain takes at most 5; an MX exchange must resolve; an address needs a postcode (`env.contact.postcode.min_count`);
CREATE-AUTHINFO1 without an expiry gives one two days ahead (#134); handles come back in upper case and IPv6
addresses uncompressed; the IDN repertoire holds `ñ`, which the `de` table of the EPP test server does not
(`env.domainName.name.lgr.latn_enye_supported`); a read reusing a client transaction id is not refused, only a write
would be (`env.session.cltrid_reuse_supported`); an `lgr` on an ASCII name is not refused, RRI takes no LGR
(`env.domainName.name.lgr.ascii_supported`); clearing a contact's name or email is refused by RRI with 422 `02306`
(`env.contact.name.min_count`), where EPP cannot clear them and the proxy refuses with 501
(`profile.contact.name.removable`). [config.rri-mtest.yaml](../../config.rri-mtest.yaml) offers `latn-1.0` as the
LGR.

## Selectors

A case file says which backends a case, a step or an expected value is for (implemented in
[selectors.py](../../tests/helper/selectors.py)). A selector is an object whose keys name facts and which holds when
every key holds. `profile.<path>` is a leaf of the `BackendProfile` of the app under test, `env.<path>` one of the
environment's `facts`, by a dotted path. A value holds when the fact equals it; `{"contains": x}`, `{"min": n}`, `{"max": n}` and
`{"not": v}` test a collection, a number or the opposite. A list of selectors holds when one of them does. There is
no selector on the backend's name: a difference is stated as the fact it comes from. What the proxy checks before
any command is a profile fact ([Backend profile](architecture.project.md#backend-profile)); what only the server
decides, and the tests read, is an environment fact.

Facts and profile are trees of the same shape: `<object>.<field>.<leaf>` and `<object>.processes.<process>.<leaf>`,
objects and fields by their RPP names (`domainName.authInfo`, `contact.postcode`), and `session` for what is not of
an object. A leaf means the same wherever it is:

| Leaf | Means |
|---|---|
| `min_count`, `max_count` | how many the field holds; presence is `min_count: 1`, for a single value too |
| `min_length`, `max_length` | the length of a value, in characters |
| `<what>_supported`, `supported` | whether the server takes it (rather than `<what>_refused`) |
| `<what>_required` | whether a value must have it, such as `upper_and_digit_required` |
| `changeable`, `removable` | whether an update can change or clear the field |

`null` says the field is not there or the limit is not known. A defect of a server that breaks cases is a fact under
`bugs`, with its issue in the comment, so the cases it breaks do not run there (`env.bugs.over_max_length_cut`).
Facts are in block style, without `{}`.

| Where | Form | Effect |
|---|---|---|
| A group | `_group.json` in the group directory: `{"when": …}` | every case of the group is skipped where it does not hold |
| A case | `"when"` at the top level | the case is skipped where it does not hold |
| A step | `"when"` in the step | the step is left out. A step with `when` cannot `capture` |
| Any value of a step | `{"select": [{"when": …, "then": …}, …, {"then": …}]}` | the `then` of the first entry that holds; the last entry is the default. An entry `{"omit": true}` instead of `then` leaves the member or list element out |

Selectors are resolved first, then the placeholders, then the captures. A selector key that names no fact, in any
known environment, fails the case at load. A skip names the facts that did not hold. A case whose selectors skip it
in every known environment fails, because it never runs. `any_of` stays for what the protocol leaves to the server,
`select` is for what differs by backend or server, and `"skip": "#<issue>"` for a known defect. A case never accepts
a success and a refusal at once: where servers decide differently, one case each states the answer, selected by the
fact that tells them apart (a server policy is an `env` fact, such as `contact.postcode.format_by_country`), and a twin that
no known environment would run is not written.

## Waiting for a period

The lifecycle periods of a server are facts of its environment, ISO 8601 durations under the process they belong to:
`domainName.processes.create.add_grace_period`, `…delete.redemption_period`, `…delete.pending_delete_period`,
`…restore.pending_period`, `…transfer.pending_period`, `…renew.grace_period` and the others in the environment
files, and `contact.processes.transfer.pending_period`. A period is the longest the transition takes there: a server
that runs it by cron adds its interval, one stated as a time of day its longest case. `null` says the server has no
such transition, `PT0S` that it is immediate.

A step writes `"wait": "<path>"` (or a list of paths, which add up), and the runner sleeps for the period and a
buffer of `RPP_TEST_WAIT_BUFFER` percent (default 10) before its request. A case names every period it waits for in
its own `when` as `"wait.<path>": true`, which a load checks. That selector holds where the server has the
transition and its wait is within `RPP_TEST_MAX_WAIT` (an ISO 8601 duration, default `PT10M`); otherwise the case is
skipped with the wait it needs. Each wait is held to the maximum on its own. A case that runs nowhere is looked for
without the maximum, so a case of a day is not reported as broken:
`RPP_TEST_MAX_WAIT=P2DT6H RPP_TEST_ENV=rri-mtest pytest -k domain_lifecycle-test8` runs the RGP and the purge of
MTEST. `domain_create/test44` (a `failed` domain deleted by DENIC after a day) has not been run yet.

## Tests without the backend

Unit tests in `tests/unit/` inject test doubles through constructors:

- `EPPClient(transport, username, password)` takes a fake transport.
- `EppBackend(epp_client, ns_map, profile, idn_tables=None)` takes a fake client, such as
  [FakeEppClient](../../tests/helper/fake_epp_client.py), and a flow takes that backend. Tests pass
  [EPP_NS_MAP](../../tests/helper/epp_ns_map.py), the namespace map of `config.yaml`, which the XML tests assert;
  the `*_xml` functions take it as `ns_map`, and the domain ones `IdnTables` as `idn_tables`.
- `SessionPool(backend_factory)` takes a factory returning a backend.
  [epp_backends](../../tests/helper/epp_backends.py) turns a factory of fake EPP clients into one, so the test still
  sees the clients.
- `create_app(sessions, profile)` builds a full app around that session pool and a `BackendProfile`
  (`EPP_PROFILE` or `RRI_PROFILE` of [profiles.py](../../tests/helper/profiles.py), the generic profiles; a test
  changes one with `with_changes({"contact": {"fax": {"supported": False}}})`), so a handler can be tested through
  `test_client()` without a registry. See [test_app_injection.py](../../tests/unit/test_app_injection.py).
- The domain mappers take `profile=EPP_PROFILE`. A test that calls `map_request` directly uses the fixture of
  [epp_app_context](../../tests/helper/epp_app_context.py), from which `map_request` names the backend.
- `RriBackend(FakeRriClient(replies=[...]), RRI_PROFILE)` runs the RRI adapter over RRI XML replies
  ([fake_rri_client.py](../../tests/helper/fake_rri_client.py)); the replies recorded from MTEST are in
  `tests/unit/rri_replies/`, with personal data replaced. `rri_backends(factory)` builds an app around them, as
  `epp_backends` does.
- `TCPClient(host, port, tls_context)` connects to a
  [LoopbackEppServer](../../tests/helper/loopback_epp_server.py). Its certificate is
  generated per test session with the `openssl` CLI, so no key is in the repository.

## Test data format

[tests/integration/conftest.py](../../tests/integration/conftest.py) collects every `*.json` under
`tests/integration/test_case_data/<group>/` as one test per environment, named by its `test_id` (the file name
without `.json` by default), in a tree of `file_cases.py` › environment › group › case. A case whose selectors do not
hold in an environment is marked skipped there while collecting, with the facts that did not hold. A file that cannot
be loaded is still listed and fails. The runner is [file_cases.py](../../tests/integration/file_cases.py). Each file is a `steps` sequence (e.g. create →
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
  for behaviour the protocol leaves to the server, such as the head of a shared message queue. The alternatives are
  all successes or all refusals, never both (see *Selectors*).
- A step's `capture` maps a name to a dotted field of its response body, where a number picks a list element (`0.id`). Later steps write `{capture:name}`
  in their request or expected response, and `{capture:name+Ny}` for that timestamp N years later. It is how
  a renew sends the exact current `expiryDate`, see `domain_renew/test10`.
- A step's `wait` names a period of the environment, or a list of them that add up, which must pass before its
  request; see [Waiting for a period](#waiting-for-a-period).
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

`"markers"` at the top level lists pytest markers of the case, each registered under `markers` in `pyproject.toml`
(an unknown one fails the case). `smoke` marks the smoke suite, `pytest -n 4 -m smoke`, to run on every iteration:
one happy path of each operation, without a `wait`. Most run on every backend; those of an object a backend lacks
(hosts on RRI) are skipped there, as any case is.

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
`02004`, `02005`) or 422 (`02306`), never 500 or 501. A limit that differs by server is a fact of the environment
(`contact.city.max_length`), and `bugs.over_max_length_cut` marks a server that stores a value cut instead of refusing
it, where the cases over a column do not run. The EPP test server cuts strings (pawel-kow/epp#21) and phone extensions (pawel-kow/epp#31),
breaks on a label of 61 to 63 characters under `.example` (pawel-kow/epp#30), and counts nameservers, contacts a role
and host addresses per command, so an update can pass its limits (pawel-kow/epp#29). It sends no reply to a domain
create that names one contact twice in a role (pawel-kow/epp#32), and refuses a `hostAttr` without addresses, also of
an external host (pawel-kow/epp#33), so `ns` records cannot be added to a domain there. A duplicate the drafts leave
open (a status, contact, nameserver, `ns` or DS record given twice) is taken or refused as the server decides, each
case pins that server's answer.
The limits and their sources are in [backend-limits.yaml](../testing/backend-limits.yaml),
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
