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
waits about 14 minutes), and as long again for `epp-docker-checked` over the same server. The unit tests are bound by CPU,
mostly building an app per test from `openapi.yaml`, so more workers than cores do not speed them up, and the backend refuses logins under about
16 concurrent sessions (pawel-kow/EPP-server-docker#7), so 8 is the most it takes: 8 workers for one of its
environments, 4 for both. Every worker makes its own `{random_name}` and `{random_id_10}` for each environment, so cases
in different workers, and the same case in two environments over one server, do not collide.

## Backend

Integration tests require a **backend EPP test server**. They do not use test
doubles: they exercise the full RPP→EPP→RPP round trip against a live registry.

Its host and port come from [config/environments/epp-docker.yaml](../../config/environments/epp-docker.yaml)
(`rpp_epp_host`/`rpp_epp_port`) via `new_epp_client` in [src/main.py](../../src/main.py). The backend is a docker
compose project (today `epptest`), and that config names its EPP server by the compose service name, `epp-server`, on TLS port `743`. That name
resolves on the project's network, `<project>_epp_net` (today `epptest_epp_net`), which the devcontainer has to
join: `postStartCommand` in [.devcontainer/devcontainer.json](../../.devcontainer/devcontainer.json) joins it on every
start (#111). Where the backend was not up then, attach it by hand:
`docker network connect epptest_epp_net <container>`, where `<container>` is the devcontainer's id (`cat /etc/hostname`
inside it); `getent hosts epp-server` shows whether it resolves. Without it every
integration case fails with 401 (`02200`). Its certificate is self-signed and does not name that host, so
the config sets `rpp_epp_tls_insecure_skip_verify`. Where the backend has another name, put it in an untracked
`config/environments/epp-docker.local.yaml` (`rpp_epp_host: <name>`), which merges over the config.

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
losing registrar). So the run setup and teardown drain the queues of `a` and `b` (`_run.json`, see
[Phases, includes and loops](#phases-includes-and-loops)), every case whose transfer request succeeds takes the mutex
`message_queue`, and one that ends with the transfer pending cancels it in its teardown, since the server approves it
minutes later and queues messages then. A case that reads a queue takes the mutex too, drains the queue in its setup
and asserts the message its own transfer queued, with the exact `RPP-Queue-Size` where the server queues nothing of
its own (`env.message.queue.server_notices`, false here): `message/test1` reads empty queues, `message/test6` its own
transfer request. The backend returns the id of the acknowledged message in the `msgQ` of an ack reply.

A contact `chg` of a `postalInfo` form replaces it: the address members not sent again (`sp`, `pc`) are wiped, also when
only `name` or `org` is sent, so the proxy sends every changed form complete (pawel-kow/epp#22). A `chg` of a form the contact does not have
is ignored although the reply is 1000 (pawel-kow/epp#23), so the proxy answers 500 (`02400`) for it (`contact_update/test33` and `test34`), and the cases that change a localization change an existing one (`test8`). Removing a status or name server the object does not have succeeds (`env.update.remove_absent_supported`), so `test6` and `test19` end on a direct `remove` of an absent label that answers 200. Adding a status or address the object has is refused with `2306` (pawel-kow/epp#18, `env.update.add_existing_supported`: `host_update/test32`, `limits_host/test12`). Both are facts of the server, which the proxy passes a PATCH to as an EPP `<update>` without a read: epp-docker names `epp-compatibility` in `informational_profiles`, so the 422 `02308` of that profile are selected where the proxy checks it (`profile.informational_profiles`): on [epp-docker-checked](#epp-docker-checked), where a PATCH is applied to the object read, adding what the object has is no change (200) and removing what it lacks is 422 `02308`.
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

The IDN tables of the backend are `de` and `es`, and `config/backends/epp.yaml` maps `latn-1.0` to `de` only, so a read with an
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
before any test module imports `main`). The descriptor holds the config file of the app under test (by default
`config/environments/<name>.yaml`, the config of the same name; `config:` names another), the most workers it
allows, the requests a minute per registrar (`rpp_requests_per_minute`, paced
by [pacer.py](../../tests/helper/pacer.py)), the registrars, a user the backend does not know, and its `facts`: only
the singular exceptions of its server, its defects (`bugs`). The other facts are the config's `rpp_protocol_config`,
which the descriptor's `facts` merge over (see [Selectors](#selectors)). The
`BackendProfile`, the TLD, the environment name and the LGRs are read from that config, as the app reads them, and not
repeated. A run with more workers than an environment it tests allows does not start.

A descriptor is layered like the configurations ([config/README.md](../../config/README.md)): `include:` names the
layers it builds on (`environments/common/rri.yaml` holds what `rri-mtest` and `rri-local` share, `epp-docker-checked` includes `epp-docker.yaml`, the `sqlite-demo-*`
descriptors include `sqlite-demo.yaml`), mappings merge and other values replace, and `null` is a fact like any value.
An untracked `<name>.local.yaml` next to a descriptor or a common layer changes it on one machine; it is no environment
of its own.

The descriptor's `preset` is the key of the RPP preset (`epp-compatible`, `rri`, `planets`, `base`) that the placeholders of
the preset headers stand for. The runner adds and rewrites nothing: every request of every case states its preset headers in
the case, `"RPP-Preset": "{rpp:preset}"`, `"Accept": "{rpp:accept}"` and `"Content-Type": "{rpp:content-type}"` (on
every request, one without a body too, core §13), and the runner resolves each as a whole header value from the
descriptor's `preset` and the `rpp_preset_signalling` of its config (`with_rpp_headers`):

| Placeholder | `header` | `media-type` |
|---|---|---|
| `{rpp:preset}` | `preset=<id>;version=1.0` | omitted: the header is not sent |
| `{rpp:accept}`, `{rpp:content-type}` | `application/rpp+json` | `application/rpp+json; preset="<id>"; preset-version="1.0"` |

Each placeholder takes the key of a preset of the environment's config, `{rpp:preset:planets-atmosphere}`, `{rpp:accept:planets-atmosphere}`
and `{rpp:content-type:planets-atmosphere}`, for a request under a preset other than the descriptor's, resolved by the same signalling method.

A header the case writes literally is sent as written, so a case can send what the runner would not (a value of another
media type, a preset the server does not offer). The signalling method is the environment fact `env.preset_signalling`
(`header` or `media-type`, read from the config, not stated twice). The cases of `preset_signalling_header/` and `preset_signalling_media_type/` hold literal headers and are each active for one
method (a case-level `when` on that fact), so a case that needs a backend as well as a method runs only where an
environment has both (the rri-only refusals are in `preset_signalling_media_type/`, as no RRI environment uses the header); a step that differs per server selects by the facts, for example `profile.presets` contains `rri`, never by the
backend's name. An expected `content_type` without parameters is the media type of the response whatever its
parameters; one with parameters is the whole value.

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
| `{regacc:a}` | the sponsor id of `a`: its login on EPP, the RegAccId of its login on RRI, its user on the SQLite demo backend |
| `{tld}` | the TLD the environment registers under, the first of `rpp_tlds` of its config |
| `{env:environment_name}` | `rpp_environment_name` of its config |
| `{env:preset_signalling}` | `rpp_preset_signalling` of its config |
| `{env:<path>}` | a fact of the environment. A list fact is a whole value only, and the response may hold any of its entries: `"label": "{env:domainName.processes.create.success_status}"` |
| `{lower:TEXT}` | TEXT in lower case, after the placeholders in it, for an id sent in another case than stored |

A descriptor's `server` names the backend server it runs over, by default the environment's own name. Environments
that name the same server share it: its mutexes (`exclusive`), its run setup and teardown, and its sessions, so the
workers of a run times its environments over the server are at most the server's `max_workers`.

### epp-docker-checked

`epp-docker-checked` is `epp-docker` with the EPP Compatibility Profile checked by the proxy
([config/environments/epp-docker-checked.yaml](../../config/environments/epp-docker-checked.yaml):
`informational_profiles: []`): the same server (`server: epp-docker`), registrars and facts. A request that breaks the
profile answers 422 `02308` there, and a PATCH under it is applied to the object read for it, so a case that differs
selects on `profile.informational_profiles`. `RPP_TEST_ENV=epp-docker,epp-docker-checked pytest -n 4` runs both.


`RPP_TEST_ENV=sqlite-demo pytest -n 4 tests/integration` runs the cases of the demo backend (`planet_*`, `satellite_*`,
`planet_transfer`, `planet_message`, `sqlite_drafts_objects`) against an app composed from
[config/environments/sqlite-demo.yaml](../../config/environments/sqlite-demo.yaml), with a database in memory per worker. It needs no credentials and no server:
the descriptor marks its registrars `literal`, so `user`, `password` and `prefix` are the values themselves, the DEMO
values of the config (they are no secrets). It has four registrars: `a` and `b` for the cases, and `c` and `d` for the
cases of the message queue only, so that no other case adds to those queues. Its facts are null but the session's (it
holds no domains or contacts), and its `bugs` those of `epp-docker`, which
no selector of its cases reads: every group of the drafts' objects has a `_group.json` with
`{"when": {"profile.objects": {"contains": "contact"}}}` (or the object), so that those groups run where the backend holds
them. The extension registers its RPP preset `planets`, which the descriptor names: `load` registers the extensions of the
config before it looks the preset up. The cases are in the smoke suite.

#### The demo configurations

[sqlite-demo](../../config/environments/sqlite-demo.yaml) is the bare configuration (the planets preset only), the `config.demo-bare.yaml` of #180:
there is no second file. Three more, which include it, compose the demo extensions, profiles and presets of #179, each with an environment of its own
(descriptor `preset` = the default preset of its config, no credentials, cases in the smoke suite):

| Config / environment | Presets (default first) | Bound profiles | Signalling |
|---|---|---|---|
| `sqlite-demo-extended` | base, planets-complete, planets, planets-atmosphere, planets-orbits | none | header |
| `sqlite-demo-bound` | base, planets, planets-atmosphere, planets-complete, catalogued-planets | planets: rocky-planets, planets-atmosphere: habitable-atmospheres, planets-complete: habitable-rocky-planets | media-type |
| `sqlite-demo-inherit` | base, planets-complete, planets, planets-atmosphere, planets-orbits, catalogued-planets, habitable-worlds | none | header |

The groups of the plain objects run in every one of them. `demo_discovery/`, `demo_preset_read/` and `demo_binding/` show the
composition of each (a case is selected by `profile.presets`, `profile.default_preset` and `profile.bound_profiles`, whose map
`contains` tests a preset key), and the criterion pair: the same planet of the type gas-giant is accepted under `planets` on `sqlite-demo` and
refused with 422 `02308` and the profile rocky-planets on `sqlite-demo-bound`. Five generic cases that create other types than rocky are
skipped on `sqlite-demo-bound`, and `sqlite_drafts_objects/test5` (the discovery of the bare server) where more presets are offered. A list in an expected body must have the length of the actual one, so a profile or extension listed twice fails.
Exact assertions over each real config file are in [test_demo_configurations.py](../../tests/unit/test_demo_configurations.py).

The configurations that must not start are in [tests/refused_configs/](../../tests/refused_configs/), not in an environment: a binding that lacks
a required extension (directly, and through a base profile), a preset cycle, a profile cycle and one extension in two versions.
The definitions of the cycles and of the two versions are test-only (`preset_cycle.py`, `profile_cycle.py`, `version_clash.py`, each a data-only extension
with a SQLite part without tables), as the demo extensions define valid ones only.
[test_refused_configurations.py](../../tests/unit/test_refused_configurations.py) composes each file and pins the message, which names both sides
of the conflict, and starts the server process once to see it exit with the message.

### DENIC MTEST

`RPP_TEST_ENV=rri-mtest pytest -n 4 tests/integration` runs the suite against DENIC's RRI test environment alone through
[config/environments/rri-mtest.yaml](../../config/environments/rri-mtest.yaml). It needs the IPv4 address of the machine on the allowlist of
both RegAccs (the devcontainer goes out with the host's address), and the `TEST_RRI_*` variables in `.env`: the two
logins, their passwords, and the prefix of the handles the cases create (it starts with the RegAccId; with the 10
random characters it leaves 4 for a case's suffix, as a handle has at most 32). Of the run's limits: 4 sessions and 100 RRI requests a minute per RegAcc, so at most 4
workers and 25 RPP requests a minute per registrar, paced by the runner. A session dropped without LOGOUT counts
until its idle timeout of 5 minutes, and a LOGIN past the limit is refused with `73100000005`, so each worker logs its
sessions out when the run ends (`pytest_sessionfinish`, `SessionPool.close`); a killed run cannot, and the next run
within 5 minutes may be refused. Two runs at once (a terminal and VS Code) share the 4 sessions. 10 failed LOGINs lock a user for an hour,
so the failed logins are of an unknown user. A RESTORE is one step and needs no wait; the RGP and the purge after it
take up to two days, which a run waits for only with `RPP_TEST_MAX_WAIT` of `P2DT6H` or more. MTEST keeps what the cases create: they delete their domains, and the contacts stay (RRI cannot delete
one), which the random part of the handle keeps apart from other runs. The random part is the same for the whole run, so a handle's suffix is unique across all cases (#188). Every case runs on both backends unless it needs a function one of them lacks, which its `when`
names: host objects, client statuses, `ds` records, registration periods, renew, a transfer process (`domain_transfer/`, which RRI's
immediate CHPROV has not; `domain_transfer_ext/` is its counterpart with the `rri` extension, run on MTEST only), the
request contact object (`request_contact/`, `profile.objects` contains `requestContact`), the organisation read (`organisation_read/`, `profile.objects` contains `organisation`; `organisation_not_held/` is its counterpart on a backend without it, 501 `02307`) or a domain's request contacts
(`profile.domainName.abuse.max_count` at least 1: `domain_update/test37`, `limits_domain/test20`), the authorisation information processes of the `rri` extension (`authinfo_process/`, `profile.domainName.processes.authInfoProcess.operations` and `authInfoIssueProcess.operations` contain `create`; its domains have no `authInfo` of their own, the expiry date is `{date:+1d}` because MTEST accepts no other, #134), the verification information of contacts and the verification process of the `rri` extension (`contact_verification/`, `profile.domainName.processes.verificationProcess.operations` contains `read`; MTEST sets a deadline for a domain of a holder whose verification failed within seconds, so `test6` polls the process, paced by `rpp_requests_per_minute` and bounded by `max_iterations`; absence of `verifications` is shown by a `remove` with a `match` that answers 422 `02308`, as above), contact transfers, a restore report, a period longer than the run waits,
contact delete, a contact's authInfo, a localization, a fax, a region, a changeable contact name, a person's name
on an organisation, a readable domain authInfo, or the admin, tech and billing roles. Where the
backends differ in what a case sends or expects, the case selects by the fact: a contact has a phone and a full
address on both (RRI requires them); a domain gets an `a` record (`profile.domainName.dns.min_count`) and a
registrant, created in the case's setup (`profile.domainName.registrant.min_count`); a domain gets no
General Request or Abuse contact, which RRI does not require (`profile.domainName.generalRequest.min_count` and
`abuse.min_count`, leaves of the rri extension, are 0; a profile without the extension has none, and a selector reads them as null), so the cases that work alike on both backends leave them out, and only the cases about them
create them, in their setup; `expiryDate`, the provisioning metadata RRI does not
show (`profile.domainName.metadata`) and a domain's authInfo are left out where they do not apply; the status a domain
reads with right after its create is one of `env.domainName.processes.create.success_status` (`ok` on the EPP test
server; on MTEST `pendingCreate` while the predelegation check runs, `ok` once it passed). A case gives DNS data that
passes the check (an `a` record DENIC serves itself), unless the check is its subject: name servers that do not serve
the domain make it `inactive` (`env.domainName.processes.create.failed_dns_status`, `domain_create/test43`), and an
update with them is refused where `env.domainName.processes.update.dns_checked` (`domain_update/test48`). Passwords
are of the characters an RRI AuthInfo takes. Where a function exists on one backend only, a counterpart case covers
the other (`domain_update/test37`, `domain_lifecycle/`). Where the cases would have the same subject and differ only in
steps of a function one backend lacks, they are one case whose steps say where they run (`domain_restore/test1`,
`domain_update/test30`, `limits_domain/test22`, `message/test6`).

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
(`profile.contact.name.removable`). [config/environments/rri-mtest.yaml](../../config/environments/rri-mtest.yaml) offers `latn-1.0` as the
LGR. QUEUE-DELMSG states no count of the messages left, so the proxy answers an acknowledge without `RPP-Queue-Size`
(#172, `env.bugs.queue_del_no_msgcnt`, `message/test6`). DENIC queues notices of its own
(`env.message.queue.server_notices`): a `domainStatusUpdate` of a domain some time after a case created it, a
`contactDelete` of its housekeeping, so `message/test6` acknowledges the heads that are not its own until the
`chprovAuthInfo` notice of its transfer (a `transferOutcomeMessage`, also read by `?type=transferOutcomeMessage`) is the head. A first run drained a backlog of about 2900 messages; the run setup
drains at the registrar's whole rate, as the other workers of the environment wait for it.

### Local RRI

`RPP_TEST_ENV=rri-local pytest -n 4 tests/integration` runs the suite against an RRI test server on the machine through
[config/environments/rri-local.yaml](../../config/environments/rri-local.yaml), with the `TEST_RRI_LOCAL_*` variables in `.env` (as `TEST_RRI_*`
for MTEST), so that a run with MTEST's credentials only does not test it. The config names the server's container on
Docker's default bridge network (`172.17.0.8`); another host goes in an untracked `config/environments/rri-local.local.yaml`
(`rpp_rri_host: <host>`). Its facts are MTEST's, except that its predelegation check passes every create and update
(`failed_dns_status: null`, `update.dns_checked: false`, so `domain_create/test43` and the update cases of a check do
not run), and that it allows 2000 RPP requests a minute per registrar.

## Selectors

A case file says which backends a case, a step or an expected value is for (implemented in
[selectors.py](../../tests/helper/selectors.py)). A selector is an object whose keys name facts and which holds when
every key holds. `profile.<path>` is a leaf of the `BackendProfile` of the app under test, `env.<path>` one of the facts:
the `rpp_protocol_config` of its config with the descriptor's `facts` merged over it, by a dotted path. A value holds when the fact equals it; `{"contains": x}`, `{"min": n}`, `{"max": n}` and
`{"not": v}` test a collection, a number or the opposite; a `null` fact has no member and meets no bound. A list of
selectors holds when one of them does. There is
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

`null` says the field is not there or the limit is not known. Every environment states the same facts, with `null` for one it does not know
([config/common.yaml](../../config/common.yaml) states every path as `null`, and each layer what it knows: the protocol
what its specification fixes, or DENIC's rules for RRI, the backend its server's policy and periods, the environment
what is its own): a
case's selectors are checked against every environment when it loads (`test_every_environment_states_the_same_facts`). A defect of a server that breaks cases is a fact under
`bugs`, with its issue in the comment, so the cases it breaks do not run there (`env.bugs.over_max_length_cut`). A `when` names the fact the case depends on,
not another that happens to go with it on today's backends (`aaaa` records do not stand in for "no host objects").
Facts are in block style, without `{}`.

| Where | Form | Effect |
|---|---|---|
| A group | `_group.json` in the group directory: `{"when": …}` | every case of the group is skipped where it does not hold |
| A case | `"when"` at the top level | the case is skipped where it does not hold |
| A step, block or loop | `"when"` in it | it is left out. A step with `when`, or in a block with one, cannot `capture` |
| Any value of a step | `{"select": [{"when": …, "then": …}, …, {"then": …}]}` | the `then` of the first entry that holds; the last entry is the default. An entry `{"omit": true}` instead of `then` leaves the member or list element out |

A group or case `when` that skips it somewhere has a `"comment"` next to it, which says in which environment it is
skipped and why, in terms of the backend; the runner ignores it. Every step starts with a `"comment"` too: what it
sends, what it expects, and why it is there (setup, the check of the case, a read back, cleanup), and where it runs
when it has a `when`. A comment holds no `{` or `}`, since the runner replaces placeholders in every string.

Selectors are resolved first, then the placeholders, then the captures. A selector key that names no fact, in any
known environment, fails the case at load. A skip names the facts that did not hold. A case whose selectors skip it
in every known environment fails, because it never runs. `any_of` stays for what the protocol leaves to the server,
`select` is for what differs by backend or server, and `"skip": "#<issue>"` for a known defect. A case never accepts
a success and a refusal at once: where servers decide differently, one case each states the answer, selected by the
fact that tells them apart (a server policy is an `env` fact, such as `contact.postcode.format_by_country`), and a twin that
no known environment would run is not written.

## Waiting for a period

The lifecycle periods of a server are facts of its backend (`rpp_protocol_config`), ISO 8601 durations under the process they belong to:
`domainName.processes.create.add_grace_period`, `…delete.redemption_period`, `…delete.pending_delete_period`,
`…restore.pending_period`, `…transfer.pending_period`, `…renew.grace_period` and the others in the config
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
  [EPP_NS_MAP](../../tests/helper/epp_ns_map.py), the namespace map of `config/protocols/epp.yaml`, which the XML tests assert;
  the `*_xml` functions take it as `ns_map`, and the domain ones `IdnTables` as `idn_tables`.
- `SessionPool(backend_factory)` takes a factory returning a backend.
  [epp_backends](../../tests/helper/epp_backends.py) turns a factory of fake EPP clients into one, so the test still
  sees the clients.
- `create_app(sessions, profile, registry=...)` builds a full app around that session pool and a `BackendProfile`
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

### Supported Python versions

The proxy supports every Python in bugfix or security status ([devguide.python.org/versions](https://devguide.python.org/versions/)),
3.11 to 3.15 on 2026-11-20 (#213). [test_python_versions.sh](../../test_python_versions.sh) installs `requirements-dev.txt`
in a `python:<version>-slim` container of each, which has no compiler, so a pin without a wheel for that Python fails,
and runs the unit tests marked `pyversions`. The workflow `.github/workflows/python-versions.yml` runs it on every push
to `main`, every PR and weekly. The marker is on one test per native or version-sensitive dependency: EPP XML (`lxml`,
`xsdata`), RRI XML, the app (Connexion, Starlette, `jsonschema`, `rpds-py`), the SQLite backend (SQLAlchemy,
`greenlet`), the settings (PyYAML) and TLS (`ssl`); a new such dependency gets a test marked too. When a Python
version is released or reaches its end of life, update the default list of the script and this section.

## Test data format

[tests/integration/conftest.py](../../tests/integration/conftest.py) collects every `*.json` under
`tests/integration/test_case_data/<group>/` as one test per environment, named by its `test_id` (the file name
without `.json` by default), in a tree of `file_cases.py` › environment › group › case. A case whose selectors do not
hold in an environment is marked skipped there while collecting, with the facts that did not hold. A file that cannot
be loaded is still listed and fails. The runner is [file_cases.py](../../tests/integration/file_cases.py). Each file is a `steps` sequence (e.g. create →
update → verify) run against a Flask test client, with an optional `setup` before and `teardown` after it (see
[Phases, includes and loops](#phases-includes-and-loops)). `RPP_TEST_CASE_DATA` names another case directory, which
the tests of the runner itself use ([test_case_phases.py](../../tests/unit/test_case_phases.py)).

- Placeholders `{random_name}`, `{random_id_10}`, `{test_start}` (start of the case)
  and `{unique_cltrid}` (new value per occurrence, and per run of a step a loop repeats: a step's placeholders are
  replaced right before it runs) keep tests idempotent against a
  shared registry. A contact id is `{handle:a:SUFFIX}`, because the backend requires the prefix of its registrar. `{ulabel:TEXT}` is the U-label
  `TEXT-<random_id_10>` and `{alabel:TEXT}` its A-label, so an IDN case writes `{alabel:bücher-t24}.{tld}`.
  `{upper:TEXT}` is TEXT in upper case, after the other placeholders in it are replaced. The backend stores host
  names in upper case, so a `match` on a generated host writes `{upper:ns1.u17-{random_name}.net}`.
  `{pad:N:TEXT}` is TEXT followed by the digits 0 to 9, repeated, to N characters, for a name or id of an exact
  length that keeps the random part of TEXT: `{pad:63:t3-{random_name}}.{tld}` is a label of 63.
  `{date:+Nd}` is the date (`YYYY-MM-DD`) N days from today in the zone of the registry (Europe/Berlin), for a date the registry limits to a period
  from now, such as the expiry of authorisation information.
- Every step asserts the headers of core §6.2: `RPP-Svtrid`, a 5-digit `RPP-Code`, and
  `RPP-Cltrid` echoed.
- Response body comparison is **subset + case-insensitive**
  (`recusive_compare_existing`) and lists match unordered, each expected element pairing
  with an actual element of its own, because EPP servers may
  uppercase domain/host names and reorder list entries (see
  [RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md)).
- A step's `response` can be `{"any_of": [...]}`, a list of responses of which one must match,
  for behaviour the protocol leaves to the server, such as whether a queue is empty. The alternatives are
  all successes or all refusals, never both (see *Selectors*).
- A step's `capture` maps a name to a dotted field of its response body, where a number picks a list element (`0.id`). Later steps write `{capture:name}`
  in their request or expected response, and `{capture:name+Ny}` for that timestamp N years later. It is how
  a renew sends the exact current `expiryDate`, see `domain_renew/test10`.
- A step's `wait` names a period of the environment, or a list of them that add up, which must pass before its
  request; see [Waiting for a period](#waiting-for-a-period).
- `fields`/`headers` support condition dicts (`not_null`,
  `datetime_format_utc_and_delta`, …) via `evaluate_condition`. `fields` keys are dotted
  paths, for example `provMetadata.crDate`. A header that is a list (RFC 9110 §5.6.1) is checked with
  `{"type": "list_contains", "values": ["Accept"]}`: each value is an element, compared without regard to case,
  whatever else the list holds (a framework may add its own, as Starlette adds `Origin` to `Vary`) and in any order.
- `draft_domain/`, `draft_contact/`, `draft_host/`, `draft_patch/` and `draft_discovery/` hold the examples
  of the JSON draft (§8.1, §8.2, §8.3, §5.3.1, §8.7.1; the discovery one has the configured values). Examples for operations not implemented yet have the
  expected result written down and `"skip": "#<issue>"`.

### Phases, includes and loops

```json
{"test_id": "...", "exclusive": ["message_queue"], "setup": [items], "steps": [items], "teardown": [items]}
```

- **Phases.** `setup` prepares, `steps` is the operation the case checks, `teardown` cleans up; `setup`, `teardown`
  and `exclusive` are optional. A failure in `setup` is a pytest **error**, and the steps do not run; one in `steps`
  a **failure**. `teardown` runs always, also after an error or failure, step by step: a failing step is a **warning**
  in the `teardown warnings` section of the summary (and a section of the case's report), never a failure, and the
  next step runs. Captures are one namespace across the phases; one a failed setup did not take fails the teardown
  step that uses it, a warning. Every failure starts with where it happened:
  `test6 setup[0] > include drain_queue[0] > loop iteration 7[1]: …`.
- **Items.** An item of a phase is a step, an include or a loop, each with an optional `when`.
- **Includes.** `test_case_data/_includes/<name>.json` is
  `{"comment": …, "parameters": {"<name>": {"comment": …, "default": …}}, "steps": [items]}`; a parameter without
  `default` is required. An item uses it as `{"comment": …, "include": "<name>", "with": {"<name>": value}}`. In the
  include, `{param:<name>}` stands for the value: alone in a string any JSON value, within one as text
  (`"{auth:{param:registrar}}"`). The case loads with every include expanded; an unknown include, a missing or unknown
  parameter, a `{param:…}` the include does not declare and a cycle fail it at load, naming the include and the
  parameter. A parameter's default may use the other parameters. An include may use includes, and a capture in it
  serves the later steps of the case. `drain_queue`
  (`registrar`) acknowledges the messages of a queue until it is empty.
- **The cases' phases.** A case's preparation is its `setup` and its cleanup its `teardown`; `steps` holds only what
  the case checks, so a failing preparation is an error and not the failure of the operation. A preparation or cleanup
  that more than one case does comes from an include, and a case passes only what differs from the include's
  defaults, which hold what the cases have in common; it gives a value of its own only where its steps rely on it:
  - `create_contact`: `id`; `contactInfo`, Erika Mustermann in Frankfurt by default; `authInfo`, `Abc2345678` where
    the profile has a contact authInfo.
  - `create_full_contact`: `id`, `authInfo`; John Doe with a region and a fax where the profile has them, for the
    cases that change or remove those members.
  - `create_domain`: `name`; `registrant_id`, the registrant where the profile requires one, or `registrant`, a
    registrant sent everywhere; `dns`, an `a` record where the profile requires DNS data by default; `authInfo`,
    `Abc2345678` by default; and the members only some domains get (`contacts`, `nameservers`, `abuse`,
    `generalRequest`, `lgr`, `uName`, and `url` for one that asks for the authInfo back).
  - `create_host`: `name`; `dns`, its own `ns` record by default, which an external host needs.
  - `create_request_contact`: `id`, `uriTemplate`. `delete_domain`: `name`. `cancel_transfer`: `collection`, `id`,
    by registrar `b`, the requester.

  Each takes `registrar` (default `a`, the sender) and leaves out a member nobody passes (a default of
  `{"select": [{"omit": true}]}`); a default may use the other parameters (`{param:name}`). Each asserts all that its
  cases rely on: a create 201 `01000` with `application/rpp+json`, the object's `@type`, its id or name, and of a
  domain its status, registrant, contacts and sponsor. A preparation only one case does, or one that is the subject of
  the case (the preset headers of `preset_signalling_*`, the draft's examples in `draft_patch`), stays a step in the
  setup.
- **Loops.** `{"comment": …, "loop": [items]}` runs its items again and again until the response of its one step with
  `until` (in it or in its includes, not in a loop within it) matches the `until`, after it passed its `response`;
  that step then takes no `capture`. `until` has the form of a `response` and checks only what it states
  (`{"headers": {"RPP-Code": "01300"}}`). A loop ends on its `until` or on a failing step; without `"max_iterations": N` (a whole number of at least 1) it has no maximum, and with it the loop fails the case when N iterations did not end it (`contact_verification/test6` polls for the registry's risk assessment, 60 iterations, which the pacer spreads over minutes). The step
  with `until` has no `when`.
- **Mutex.** `exclusive` names shared resources. Cases of one server (the descriptor's `server`, see
  [Test environments](#test-environments)) that name the same one never run at the same time, also in different
  environments over the server and in different xdist workers: each holds a file lock from the start of its setup to the end of its
  teardown. `message_queue` is the message queues of `a` and `b`.
- **Run setup and teardown.** `test_case_data/_run.json` is `{"comment": …, "setup": [items], "teardown": [items]}`.
  The run setup of a server runs once per run, before the first case of an environment over it, in whichever worker
  and environment gets there first, while the others wait; if it fails, every case of its environments is an error
  naming it. The run teardown runs at the end, in the process that started the run, once for every server whose run
  setup ran (in one of its environments of the run); a failure in it is a
  warning. Both pace their requests at the registrar's whole rate. The workers share the run's directory,
  `RPP_TEST_RUN_DIR`, which that process makes and removes.

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
breaks on a label of 61 to 63 characters under `.example` (pawel-kow/epp#30, `bugs.long_label_cut`), refuses a
`hostAttr` without addresses, which is what `ns` records become on a backend with host objects (pawel-kow/epp#33,
`bugs.host_attr_without_address_refused`), and counts nameservers, contacts a role
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

A case creates the contacts, hosts and domains it uses, in its setup, and relies on nothing seeded in the
backend. `{random_name}` and `{random_id_10}` are the same for every case of a run, so each case adds its own part:
contacts are `{handle:a:SUFFIX}` with a suffix of the case (`ua1`, at most 16 characters in all on EPP), hosts are external
`nsN.<case>-{random_name}.net`, which need their own `ns` record at create. `domain_create/test7` creates the domain
it then finds taken.

Isolate one update facet per file (authInfo-only, hostObj add/remove,
contacts+registrant, …). `domainNames_create`, `domainNames_updatePartial` and `domainNames_update` build their
success body from a follow-up EPP **Info** call, so a passing update test also transitively
exercises Info and `domains.model_to_rpp`.

### Presets and profiles

The proxy criteria of #174 are unit tests over the wire and without an app:
[test_offered_presets.py](../../tests/unit/test_offered_presets.py) (the checks at start, each refusal naming what conflicts),
[test_schema_scope.py](../../tests/unit/test_schema_scope.py) (the two steps of validation and the validators of a preset),
[test_preset_schemas.py](../../tests/unit/test_preset_schemas.py) (the Preset Schema and its endpoint),
[test_preset_profile_constraints_wire.py](../../tests/unit/test_preset_profile_constraints_wire.py) (a profile constrains, 422
and the same request without it), [test_presets_wire.py](../../tests/unit/test_presets_wire.py) (Preset and Profile Data
Objects, discovery) and the signalling tests (`test_preset_header_wire.py`, `test_preset_media_type_wire.py`). The presets and
profiles of the tests are registered as an extension brings them, with
[test_demo_profiles_wire.py](../../tests/unit/test_demo_profiles_wire.py) (the demo profiles on the SQLite demo backend: each constraint
refused with 422 `02308` and the same request accepted without the profile, 400 for a member outside the preset, built with
[demo_app.py](../../tests/helper/demo_app.py)), [test_demo_presets_wire.py](../../tests/unit/test_demo_presets_wire.py) and
[test_demo_docs.py](../../tests/unit/test_demo_docs.py) (the specifications under docs/demo/: marked examples, `violates` for a
profile, the Preset Overview), and with
[preset_fixtures.py](../../tests/helper/preset_fixtures.py) (`registry_with(presets, profiles)`), so the multiple inheritance
and the bindings of #180 are covered without its configurations. A mapper called without an app takes its schemas from
`SchemaScope.of(extensions)`, built on first use and without profiles; an app gives a request the schemas of its preset.
