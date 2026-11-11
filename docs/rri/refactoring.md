# Refactoring for RRI as a second backend protocol

This document proposes how the proxy gets DENIC RRI 5.0 as an alternative to EPP for talking to the registry. The
RPP API stays the same. Which RRI transaction serves which RPP operation, and where they do not fit, is in
[gap-analysis.md](gap-analysis.md). The RRI facts are in [rri-5.0-reference.md](rri-5.0-reference.md), and the DENIC
XML schemas in [xsd/](xsd/). The feature is tracked as
[issue #126](https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/issues/126).

Status: **proposal, for acceptance.** Under [process.md](../agents/process.md) rule 2 and the working agreement in
[AGENTS.md](../../AGENTS.md), nothing here is implemented until the maintainer accepts it. The open questions in
[gap-analysis.md §7](gap-analysis.md#7-open-questions) and in [§8](#8-open-questions-of-this-plan) below must be
answered first.

**Prerequisite:** [#120](https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/issues/120) ("Restructure `src/`
into core, rpp and registry adapters") is merged. This plan builds on its target layout, as
[architecture.project.md](../agents/architecture.project.md#target) describes it, and its dependency rules. The RRI
adapter is `registry_adapter/rri/`, a sibling of `registry_adapter/epp/`.

## 1. Goals and non-goals

Goals:

- One deployment talks to **one** backend, EPP or RRI, chosen in configuration. The RPP wire contract (paths,
  schemas, the §18.1 code → status mapping, the `RPP-*` headers) is unchanged.
- `core`, `rpp` and the flows are written once. RRI is a new `registry_adapter/rri/` behind the existing port, and
  nothing outside it and `main.py` knows that it exists.
- The EPP behaviour stays exactly as it is.
- **One integration suite for both backends.** The data-driven cases select steps and expected results by the
  facts of the backend profile, and run against the EPP test server and against DENIC's RRI test environment
  (MTEST).

Non-goals:

- Running EPP and RRI side by side in one process, or routing by TLD.
- Exposing RRI-only functions (AuthInfo2, TRANSIT, regacc INFO, NIS2 verification) in the first version. See Q8,
  Q9, Q10 and Q16.
- The RRI K/V format (Q20).
- A local RRI stub server. MTEST is the integration backend for RRI.

## 2. Starting point

Most of what the first version of this plan proposed as preparation is done, on EPP only and without behaviour
changes:

| Done | Where it is after #120 | Issue |
|---|---|---|
| Full and partial updates kept apart down to the model: `*Replacement`, `<object>_difference`, `<object>_application` | `core/model/{domain,contact,host}/` | #108 |
| The backend port: `RegistryBackend`, the `*Gateway` protocols, `ReplaceOutcome`, `ReplacementSteps`, `derived_update.replace` | `core/ports/` | #116 |
| `BackendProfile`, `NotSupportedByBackend`, `NotSupportedByProxy`; discovery states the profile's objects and profiles | `core/capabilities/`, `rpp/handlers/discovery.py` | #117 |
| One `SessionPool` per user and backend, token info `backend` | `core/session/` | #116, #120 |
| `IdnTables` in the EPP adapter, the mapper checks `lgr` against `BackendProfile.lgrs` | `registry_adapter/epp/idn_tables.py` | #120 |
| Settings loaded once by the composition root and passed in | `settings/`, `main.py` | #120 |
| TCP client and TLS free of EPP names | `registry_adapter/common/transport/` | #120 |

What is still bound to EPP, and what this plan changes:

| Place | Binding | Changed in |
|---|---|---|
| Transport | `TCPClient` writes `len(payload) + 4` (RFC 5734 counts the header). RRI counts the payload only. | R2, §3.4 |
| Models | No apex `a`/`aaaa`/`mx` records, no `status_due`, no neutral queue events beyond `TransferEvent` and `PendingActionEvent`, no carry-over of verification data, one registrant. | R2, §3.6 |
| Port | Only the derivation full ← partial exists (`derived_update.replace`). RRI needs partial ← full. | R4, §3.5 |
| Profile | Several facts are declared but not read yet (`host_objects`, `client_statuses`, `contact_fax`, …). No facts for transfer, restore reports or a readable authInfo. | R1, R3–R7, §3.7 |
| Settings | `Settings` has the `epp` and `discovery` sections only. | R3, §3.9 |
| Integration tests | The cases hard-code EPP: credentials (`Basic Zm9vOmJhcg==` in 623 steps), contact ids (`FO-`, `BZ-` in 94 files), the TLD (`.example`), host objects, and the quirks and periods of the EPP test server. | R1, §5 |

## 3. Target design

### 3.1 The backend port

The port in `core/ports/` stays as it is. `registry_adapter/rri/gateways/` implements it: `RriBackend`,
`RriDomainGateway`, `RriContactGateway` and `RriMessageGateway`. The return types are those the EPP gateways have
after #120 phase 6 (the result envelope).

RRI has no host objects. `RriBackend.hosts` is `RriHostGateway`, whose every method answers
`ErrorResponse(UNIMPLEMENTED_COMMAND)`, the convention of the port for a command the backend lacks, so every
`/hosts` operation answers 501 `02101`. A flow asks the profile first only where it would otherwise send a wasted
read (renew without `expiryDate`, §3.5.5).

### 3.2 Session and authentication

- `RriClient` in `rri/session/` has the session contract of `EPPClient`: LOGIN with `user` and `password` and no
  greeting, LOGOUT on disconnect, a re-entrant lock around each exchange, reconnect and re-login on a dead socket,
  and a retry **only** if the command was never written. RRI writes are not idempotent, and a CTID cannot be reused
  (ref §3.3).
- An idle session expires after 5 minutes. The client reconnects on demand rather than sending a `QUEUE-READ` the
  user did not ask for.
- Lock, reconnect and re-login are now written twice. Once the RRI client works, the parts that are the same move
  to `registry_adapter/common/` ([architecture.project.md](../agents/architecture.project.md#target), rule 6 of
  [architecture.md](../agents/architecture.md)). What differs (greeting, extensions) stays in each adapter.
- **The sponsor id is per session (changes Q17).** MTEST runs with two RegAccs in one deployment (§5.4), so one
  configured `rpp_rri_regacc_id` cannot be right for both. `RriBackend.sponsor_id` is the RegAccId taken from the
  login: an RRI login is a DENIC handle, and a handle starts with the RegAccId of its RegAcc (ref §5.1,
  `DENIC-1000022-RRI` → `DENIC-1000022`). The maintainer confirmed that every RRI login follows this (P1).
- Login throttling stays out of scope, see the lockout risk in §7.

### 3.3 RRI wire format

**XML 5.0** (gap Q20):

- The server validates XML strictly against the XSDs. K/V *silently ignores unknown keywords* (ref §3.1), and under
  RRI's full-replacement update a misspelt keyword deletes stored data without an error.
- The DENIC XSDs are in [docs/rri/xsd/](xsd/). xsdata compiles them into `registry_adapter/rri/xml/generated/`, as
  the EPP XSDs are compiled into `registry_adapter/epp/xml/generated/`. The command goes into a script next to
  [copy_models.sh](../../copy_models.sh). The generated code is exempt from the one-class-per-file rule.
- `rri/xml/codec.py` renders and parses with the hardened parser of `registry_adapter/common/xmlsafe` (no entities,
  no DTD).

### 3.4 Transport

- `TCPClient` in `common/transport/` takes a `framing` argument: the length counts the header (RFC 5734) or not
  (RRI). The default is the EPP one, and the EPP composition does not change. Unit tests cover both.
- The TLS context is reused: verification on by default, `insecure_skip_verify` for test backends only. DENIC's
  certificate is a public chain, and no client certificate is needed.
- Requests are at most 64 KB. Responses are read with the same exact-length loop.

### 3.5 Full and partial updates

The model already keeps the client's intent apart: a partial update is a `*Update` delta, a full one a
`*Replacement`. The two protocols make opposite choices:

| | EPP adapter | RRI adapter |
|---|---|---|
| `update(delta)` | **Native**: one `<update>`. No read. | **Derived**: read (unless `current` is given), `wanted = apply(current, delta)`, then native `replace` |
| `replace(wanted)` | **Derived** (`derived_update.replace`, exists) | **Native**: UPDATE or CHHOLDER with the full state, plus AuthInfo commands |

#### 3.5.1 The second derivation

`core/ports/derived_update.py` gets `update(gateway, delta, current=None)`, the mirror of `replace`: it reads the
object unless `current` is given, applies the delta with the object's `<object>_application.apply`, and calls the
gateway's native `replace`. It is written once, next to `replace`, and the RRI gateways call it. A hand-written copy
in the adapter is what rule 6 of [architecture.md](../agents/architecture.md) forbids.

`apply` exists for domains, contacts and hosts and is pinned by round-trip tests against `difference`. RRI uses the
domain and contact ones.

#### 3.5.2 The native RRI replace

For a domain:

1. Read `current` if it was not given. It decides whether the holders change (CHHOLDER or UPDATE), whether an
   AuthInfo1 exists, and whether anything changes at all.
2. If nothing differs and the `authInfo` intent is to keep it, send nothing and answer `ReplaceOutcome` unchanged,
   with the `current` it read, so `core/flows/sponsor.py` still holds the 403 for a non-sponsor.
3. If the holders differ → CHHOLDER(wanted). Otherwise, if anything else differs → UPDATE(wanted).
4. A new password → DELETE-AUTHINFO1 if one exists, then CREATE-AUTHINFO1(sha256(pw)). A cleared one →
   DELETE-AUTHINFO1 if one exists. After a CHHOLDER both are skipped, because it removed all AuthInfos.
5. Answer the response of the last command, or a partial failure (gap Q7).

For a contact, step 3 is one UPDATE, and the adapter copies the verification blocks of `current` into the request,
because RPP cannot carry them and leaving them out deletes them (gap §4.5).

What a backend cannot clear stays in its adapter (`registry_adapter/epp/refusals.py`). RRI needs no such check,
because a full update clears by omission.

#### 3.5.3 Commands per RPP request

| RPP request | EPP commands | RRI commands |
|---|---|---|
| PATCH that maps directly | update, info (2) | INFO, UPDATE, [AuthInfo], INFO (3+) |
| PATCH that needs the current state | info, update, info (3) | INFO, UPDATE, [AuthInfo], INFO (3+) |
| PUT | info, update, info (3) | INFO, UPDATE, [AuthInfo], INFO (3+) |

The read-back after a mutation, and its 202 when it fails, are in `core/flows/read_back.py` and work the same for
both backends.

#### 3.5.4 Other RRI operations

- **Create with authInfo**: CREATE, then CREATE-AUTHINFO1, in the adapter. The flow keeps its read-back and its 202.
- **Domain transfer** follows gap Q3. Under option C the RRI `transfer()` answers `UNIMPLEMENTED_COMMAND`.
- **Renew**: `renew()` answers `UNIMPLEMENTED_COMMAND`. The renew flow reads `exDate` when no `expiryDate` is
  given, which would be a wasted INFO, so it asks `profile.supports_renew` first.
- **Restore**: RESTORE per gap Q6.
- **Messages**: `core/flows/message/` is protocol-neutral already (poll, then compare ids). RRI's `msgcnt` fills
  `queue_size`.

### 3.6 Models

The model must hold what either backend holds. Each change has its own tests, and the EPP mapping of each stays as
it is.

| Model (`core/model/…`) | Change |
|---|---|
| `domain/` contacts | Neutral role names (`registrant`, `admin`, `tech`, `billing`, `generalRequest`, `abuse`), several registrants (gap Q1). |
| `domain/` DNS | Apex and subdomain `a`/`aaaa`/`mx` records (RRI `Nsentry`). Name servers on RRI are host attributes only. |
| `domain/` status | `status_due` next to `status_reasons`, for the `failed` deadline (gap Q5). |
| `domain/` read | `authInfo` absent on RRI. `crDate` absent when RRI gives `before …`. |
| `contact/` | `verification` as opaque carry-over data, never rendered to RPP. |
| `message/` | A neutral `ServiceNoticeEvent` and an `ExpirationEvent`. `TransferEvent` gains an optional source, for `chprovAuthInfo`. |
| `core/result` | `ResultCode` unchanged. `ErrorResponse` gains an optional `registry_code: str` (the 11-digit DENIC code), for the detail and the logs. |

New classes go into files of their own: the known debt of several classes per file (#20) must not grow.

### 3.7 Capabilities and the backend profile

`registry_adapter/rri/profile.py` holds `RRI_PROFILE`:

| Fact | EPP | RRI |
|---|---|---|
| `contact_labels` | `admin`, `billing`, `tech` | `generalRequest`, `abuse` (gap Q2) |
| `max_registrants` | 1 | 5 (gap Q1) |
| `domain_record_types` | `ns`, `ds`, `dnskey` | `ns`, `a`, `aaaa`, `mx`, `dnskey` |
| `host_objects` | yes | no |
| `client_statuses` | yes | no |
| `contact_fax`, `contact_localization`, `contact_region` | yes | no |
| `contact_phones_max` | 1 | 1 |
| `supports_renew` | yes | no |
| `supports_contact_delete` | yes | no |
| `objects` | `domainName`, `host`, `contact` | `domainName`, `contact` |
| `profiles` | `epp-compatibility` | to be decided (§3.10) |
| `lgrs` | from `rpp_idn_lgr_tables` | none, or one configured name (gap Q11) |

**The profile states what the protocol can do; the test environment states what one server does.** A fact goes
into `BackendProfile` when it is true of every server that speaks the protocol, whoever reads it: a mapper, a flow,
discovery or the test selectors (§5.2). What one test server does (its periods, its defects, its credentials) goes
into the test environment (§5.3), never into the profile. The profile's docstring says who reads each fact, and a
fact nobody reads is removed.

New facts, each read by the proxy and by the selectors:

| Fact | EPP | RRI | Read by |
|---|---|---|---|
| `domain_transfer_operations: frozenset[str]` (replaces `supports_transfer_query`) | `request`, `query`, `cancel`, `approve`, `reject` | none (Q3 option C), or `request` (option B) | the transfer handlers, which answer 501 `02101` without a command |
| `contact_transfer_operations: frozenset[str]` | the same five | none | the same |
| `restore_report: bool` | yes | no (gap Q6) | the restore mapper, which refuses a report with 501 `02102` |
| `auth_info_readable: bool` | yes | no | the domain mapper, which refuses `includeElements=authInfo` with 501 `02102` (P2) |

### 3.8 Result codes and errors

- `registry_adapter/rri/result_codes.py` holds the DENIC code → `ResultCode` table and the class-digit fallback of
  [gap-analysis.md §5](gap-analysis.md#5-result-code-mapping), unit-tested code by code.
- The handlers render it through the existing path to core §18.1. When there is a DENIC code, the detail starts
  with it.
- A success with warning or info messages (predelegation warnings, deadline infos, MTEST's `13000000011`) is logged
  with its codes, never its arguments, because they can hold personal data
  ([security.project.md](../agents/security.project.md)).

### 3.9 Settings and composition

`settings/rri_settings.py` holds `RriSettings`, and `Settings` gains `backend` and `rri`:

```yaml
rpp_backend: epp                 # epp | rri, default epp
rpp_rri_host: rri.test.denic.de
rpp_rri_port: 51131
rpp_rri_use_tls: true
rpp_rri_tls_insecure_skip_verify: false
rpp_rri_timeout: 5
rpp_rri_lgr: null                # gap Q11
```

There is no `rpp_rri_regacc_id` (§3.2). The proxy holds no credentials: HTTP Basic is passed through as the LOGIN,
as it is for EPP.

`main.py` stays the only composition root. It reads `settings.backend`, builds the backend factory and the profile
for it, and passes both to `SessionPool` and `create_app`. There is no `if backend ==` anywhere else.

### 3.10 Discovery

`objects` and `profiles` come from the profile already. On RRI `objects` is `domainName` and `contact`. The EPP
Compatibility Profile does not describe RRI, so RRI needs its own profile URN, or a spec issue.

## 4. Package layout

The RRI adapter has the shape of the EPP one ([architecture.project.md](../agents/architecture.project.md#target)),
with `gateways → commands → xml, session` and `session → common/transport`:

```
src/registry_adapter/rri/
├── session/             RriClient: LOGIN, LOGOUT, CTIDs, lock, reconnect
├── xml/                 codec.py, generated/ (from docs/rri/xsd)
├── commands/
│   ├── shared/          the result and its messages, CTID
│   ├── domain/          rri_request.py, domain_xml.py, domain_commands.py (as epp/commands, #120 D4)
│   ├── contact/
│   └── message/
├── gateways/            RriBackend, RriDomainGateway, RriContactGateway, RriMessageGateway, RriHostGateway
├── result_codes.py      DENIC code → ResultCode
├── statuses.py          RRI status ↔ RPP status
└── profile.py           RRI_PROFILE
src/settings/rri_settings.py
tests/helper/fake_rri_client.py      replays RRI XML, like fake_epp_client.py
tests/integration/environments/      one descriptor per test environment (§5.3)
```

`import-linter` gets the contracts of `rri` in the phase that creates it: `rri` never imports `epp` or `rpp`, and
only `rri/session` sends.

## 5. Testing

### 5.1 Levels

| Level | EPP | RRI |
|---|---|---|
| Unit | `FakeEppClient` | `FakeRriClient` with replies from the DENIC examples (`EX:` pages, ref §0) and from MTEST, with personal data removed. One per transaction and per error class. They cover the update composition (UPDATE or CHHOLDER, AuthInfo sequences, verification carried over) and the result-code table. |
| Wire | `create_app` with a fake backend and `EPP_PROFILE` | the same with `RRI_PROFILE`, for the refusals the profile drives |
| Integration | the EPP test server (`epptest`) | DENIC MTEST (§5.4) |

The integration suite is **one** suite: the same case files run against each environment, and select what differs
(§5.2).

### 5.2 Selectors in the case files

A case file says which backends a case, a step or an expected result is for. A selector is a JSON object whose
keys name facts, and it holds when every key holds:

- `profile.<fact>`: a fact of the `BackendProfile` the app under test was composed with. The runner reads the
  profile from the app, so the cases never restate it.
- `env.<fact>`: a fact of the test environment (§5.3), for what one server does.

| Value | Holds when |
|---|---|
| `true`, `false`, a string, a number | the fact equals it |
| `{"contains": "admin"}` | the fact (a tuple or set) contains it |
| `{"min": 2}`, `{"max": 1}` | the fact (a number) is at least or at most that |
| `{"not": <value>}` | the inner value does not hold |

A list of selectors holds when one of them holds. A key that names no fact fails the case when it is loaded, as a
case that cannot be parsed does today, so a misspelt selector never skips silently. There is no selector on the
backend's name: a difference is stated as the fact it comes from, and a missing fact is added to the profile or to
the environment under the rule of §3.7.

Where selectors go:

| Where | Form | Effect |
|---|---|---|
| A group | `_group.json` in the group directory: `{"when": …}` | Every case of the group is skipped where it does not hold, e.g. `host_*` and `draft_host/` with `{"profile.host_objects": true}`. The runner does not collect `_group.json` as a case. |
| A case | `"when": …` at the top level | The case is skipped where it does not hold. |
| A step | `"when": …` in the step | The step is left out. A step whose `capture` a later step uses cannot have one: the loader refuses it. |
| Any value in a step | `{"select": [{"when": …, "then": …}, …, {"then": …}]}` | The first entry that holds gives the value. The last entry, without `when`, is the default and is required. |

`select` is how one step expects different results:

```json
"response": {"select": [
  {"when": {"profile.client_statuses": false},
   "then": {"status": 501, "headers": {"RPP-Code": "02102"}}},
  {"then": {"status": 200, "body": {"status": ["clientHold"]}}}
]}
```

and how a request differs, e.g. the contact roles of a domain create:

```json
"contacts": {"select": [
  {"when": {"profile.contact_labels": {"contains": "admin"}}, "then": [{"label": "admin", "object": {"@type": "contact", "id": "{handle:a:cr1}"}}]},
  {"then": [{"label": "abuse", "object": {"@type": "contact", "id": "{handle:a:ab1}"}}]}
]}
```

The selectors are resolved first, then the placeholders, then the captures. A case skipped by a selector is reported
with the facts that did not hold (`skipped: profile.host_objects is false`). The runner fails a case whose selectors
skip it in every known environment, because it never runs.

`any_of` stays for what the protocol leaves to the server, and `select` is for what differs by backend or server.
The existing `"skip": "#<issue>"` stays for a known defect.

### 5.3 Test environments

A test environment is one backend server the suite runs against. It is chosen with `RPP_TEST_ENV` (default
`epp-docker`) and described in `tests/integration/environments/<name>.yaml`:

```yaml
# tests/integration/environments/rri-mtest.yaml
config: config.rri-mtest.yaml       # RPP_CONFIG_FILE of the app under test
max_workers: 4                      # MTEST allows 4 sessions per RegAcc
rpp_requests_per_minute: 25         # paced per registrar, under the ACL of 100 RRI requests a minute
registrars:                         # the slots the cases name, each naming its variables in .env
  a: {user: TEST_RRI_REGACC1, password: TEST_RRI_REGACC1_PASSWORD,
      gen_req: TEST_RRI_REGACC1_GEN_REQ, abuse: TEST_RRI_REGACC1_ABUSE}
  b: {user: TEST_RRI_REGACC2, password: TEST_RRI_REGACC2_PASSWORD,
      gen_req: TEST_RRI_REGACC2_GEN_REQ, abuse: TEST_RRI_REGACC2_ABUSE}
handle: "{regacc}-{random_id_10}{suffix}"   # a handle starts with the RegAccId
facts:
  tld: de
  restore_within_run: false         # the RGP lasts 1 day on MTEST
  failed_logins_lock: true          # 10 failed LOGINs lock the user for an hour
```

`epp-docker.yaml` describes today's backend: `config.yaml`, 8 workers, registrars `a` = `foo`/`bar` and `b` =
`baz`/`qux`, handles `FO-…` and `BZ-…`, TLD `example`, and the facts the cases depend on today, such as the RGP in
minutes and the defects listed in [testing.project.md](../agents/testing.project.md#backend) (`env.contact_chg_of_missing_form_ignored`, …).

New placeholders take the place of what the cases hard-code:

| Placeholder | EPP test server | MTEST |
|---|---|---|
| `{auth:a}`, `{auth:b}` | `Basic` of `foo:bar`, `baz:qux` | `Basic` of the credentials in `.env` |
| `{auth:a:wrong_password}`, `{auth:unknown_user}` | `foo:cat`, `ghost:nope` | the same forms; these cases select `{"env.failed_logins_lock": false}` and do not run on MTEST |
| `{handle:a:ud1}` | `FO-{random_id_10}ud1` | `DENIC-<n>-{random_id_10}ud1` |
| `{tld}` | `example` | `de` |
| `{regacc:a}` | `foo` | `DENIC-<n>` |
| `{gen_req:a}`, `{abuse:a}` | none: EPP has no such roles, so only cases that select `{"profile.contact_labels": {"contains": "generalRequest"}}` use them | the handles in `.env` |

The MTEST values are in `.env` in the repository root, which the runner loads with python-dotenv (in
`requirements.txt` already). The proxy never reads it. `.env` is in `.gitignore`, and a committed `.env.example`
names the variables with no values:

| Variable | Holds |
|---|---|
| `TEST_RRI_REGACC1`, `TEST_RRI_REGACC2` | The RRI login of RegAcc 1 and 2 (registrars `a` and `b`), a DENIC handle whose prefix is the RegAccId (P1) |
| `TEST_RRI_REGACC1_PASSWORD`, `TEST_RRI_REGACC2_PASSWORD` | The password of that login |
| `TEST_RRI_REGACC1_GEN_REQ`, `TEST_RRI_REGACC2_GEN_REQ` | The handle of a `REQUEST` contact of that RegAcc for the General Request role |
| `TEST_RRI_REGACC1_ABUSE`, `TEST_RRI_REGACC2_ABUSE` | The handle of a `REQUEST` contact of that RegAcc for the Abuse role |

The General Request and Abuse handles are created on MTEST beforehand, outside the suite. They are the one
exception to the rule that a case creates the contacts it uses
([testing.project.md](../agents/testing.project.md#isolating-cases)): a domain on RRI needs both roles, and they
are `REQUEST` contacts, which RPP cannot create yet (gap Q2). The cases use the pre-created handles as long as RPP
has no way to create a `REQUEST` contact. Once it has, the cases create their own, and the `*_GEN_REQ` and `*_ABUSE`
variables are removed. The runner puts a credential into a request header when it sends the request,
never into the case dictionary, so a failure report cannot print it ([security.md](../agents/security.md)).

### 5.4 RRI integration tests on MTEST

- **Access.** MTEST is `rri.test.denic.de:51131`. It needs a DENIC membership, two RegAccs with an RRI login each,
  and the IPv4 address of the test machine on the allowlist of both (ref §2.1). The devcontainer behind NAT has the
  host's address. Where it has none, the MTEST run is not possible, and the plan of the phase says so.
- **Two RegAccs** stand for the two registrars `a` and `b` the cases already use: the sponsor checks (403), a
  handle of another RegAcc (`63200020603`), and a transfer once Q3 allows one.
- **Limits.** MTEST allows 4 sessions per RegAcc and 100 requests a minute. The run uses at most 4 workers, each
  holding one session per registrar, and the runner paces each registrar's RPP requests to
  `rpp_requests_per_minute`, because one RPP request can cost up to four RRI commands (§3.5.3). An ACL refusal
  fails the step with a message that names the limit.
- **Lockout.** A wrong password counts towards the lock of 10 failed LOGINs an hour, so no case with wrong
  credentials runs on MTEST, and the runner refuses to start when `.env` lacks a variable rather than log in with an
  empty one.
- **Periods.** The RGP lasts a day, so restore cases select `env.restore_within_run` and RRI's RESTORE is covered
  by unit tests. DENIC's mock-up scenarios (special names such as `NISpendingCreate`) can drive the NIS2 statuses
  later (Q16).
- **Data.** MTEST keeps what the cases create. Cases delete the domains they create. RRI cannot delete a contact,
  so the handles stay, which the random part of each handle keeps from colliding.
- **When it runs (P3).** The EPP run stays the check of [process.project.md](../agents/process.project.md#checks-before-done)
  for every change. From R3 on, a change to `registry_adapter/rri/`, `core` or `rpp` also needs a passing MTEST run,
  from a machine on the allowlist, **before it is merged**. Coding and review do not wait for it: a coder without an
  allowlisted machine runs the unit tests with `FakeRriClient`, and its plan says that the MTEST run is pending. The
  PR leaves draft only once the MTEST result is recorded in the plan. R3 adds this check to
  `process.project.md`, when there is RRI code for it to check.

### 5.5 Moving the existing cases

The cases move in R1, on EPP alone, so the EPP run proves the move:

1. A script rewrites the hard-coded values into placeholders: `Authorization` into `{auth:…}`, `FO-…`/`BZ-…` into
   `{handle:…}`, `.example` into `.{tld}`.
2. `_group.json` for the groups that need a fact (`host_*`, `draft_host`, transfers, renew, contact delete).
3. Selectors on the steps and results that depend on a defect or a period of the EPP test server, by its `env` fact.
4. The EPP run passes with the same number of passed and skipped cases as before. The plan records both counts.

The cases for RRI behaviour (several holders, `generalRequest`/`abuse`, `a`/`aaaa`/`mx` records, refused host
objects) are added in the RRI phases, as `select` entries in the existing files where the request is the same, and
as new files with a `when` where it is not.

## 6. Migration plan

One PR per phase, each following [process.md](../agents/process.md), with a branch, a `.plan/` file and the checks
of §5.4. From R3 on, a PR is merged only after a recorded MTEST pass.

| Phase | Content | Behaviour change |
|---|---|---|
| R0 | **Prerequisite**: #120 merged. | — |
| R1 | Test environments, `.env`, the placeholders and the selectors (§5.2, §5.3). The cases moved (§5.5). The new profile facts of §3.7, read by the handlers and mappers, with the EPP values. `testing.project.md` describes the selectors and the environments. | None for EPP |
| R2 | `TCPClient` framing. The models widened as in §3.6, with the EPP mapping unchanged. | None |
| R3 | `rri/session`, `rri/xml` with the generated code, CTIDs, the result-code table, `FakeRriClient`, `RriSettings`, `RRI_PROFILE`, the composition in `main.py`. `rri-mtest.yaml`. On MTEST: LOGIN and LOGOUT for both RegAccs. Then the session behaviour that EPP and RRI share moves to `common`. | New backend, off by default |
| R4 | RRI domains: CHECK, INFO, CREATE (+AuthInfo1), UPDATE/CHHOLDER, DELETE, RESTORE (Q6). `derived_update.update`. | RRI only |
| R5 | RRI contacts: CHECK, INFO, CREATE, UPDATE with verification carried over. | RRI only |
| R6 | RRI messages: QUEUE-READ, QUEUE-DELETE and the type mapping. | RRI only |
| R7 | Transfer per Q3, and what is decided for Q8–Q10 and Q16. | RRI only |
| R8 | Docs: `architecture.project.md` (the RRI adapter), `testing.project.md` (MTEST), `security.project.md` (RRI credentials, the lockout), `overview.project.md`, the README. | — |

## 7. Risks

| Risk | Mitigation |
|---|---|
| A full-replacement update loses data the proxy did not read or does not know. | XML with strict XSDs. Verification and unknown data carried over. Unit tests that INFO → UPDATE round-trips every field. |
| Read and write are not atomic, so a concurrent change between them is lost. | As on EPP today. Map `53000000012` to a status a client can retry (Q19). |
| A request of several commands fails part way. | Gap Q7. Tests for every split point. |
| Anyone with network access can lock a RegAcc out of RRI with bad logins: 10 failed LOGINs lock the user for an hour, and every HTTP Basic attempt with a wrong password for a user without a session costs a LOGIN. | **Not addressed for now**, accepted as a known risk. In the tests, no case with wrong credentials runs on MTEST (§5.4). |
| Writes are not idempotent, so a retry after a timeout duplicates or fails. | Never retry a written command. A new CTID per command. |
| An MTEST run uses up the ACL or the sessions and fails for reasons unrelated to the change. | At most 4 workers, requests paced per registrar, an ACL refusal reported as such. |
| The MTEST run needs an allowlisted machine, so RRI work could stall or be merged untested. | Coding and review go on with the `FakeRriClient` unit tests. Nothing merges without a recorded MTEST pass (§5.4). |
| Selectors make cases skip where they should run, and a regression hides behind a skip. | Unknown facts fail at load. Every skip names its facts. A case skipped in every environment fails. R1 compares the counts before and after. |
| The profile collects test-only facts. | The rule of §3.7: protocol facts in the profile, server facts in the environment. |
| NIS2 verification is not reachable through RPP, so domains end in `serverHold`. | State it in discovery and the README. Gap Q16. |
| The DENIC docs contain errors (ref §0.3). | The XSDs and recorded MTEST replies are authoritative. Each assumption from the docs is marked in its test. |

## 8. Open questions of this plan

Besides [gap-analysis.md §7](gap-analysis.md#7-open-questions):

| # | Question | Proposal | Decision |
|---|---|---|---|
| P1 | Is the RegAccId of an RRI session always the prefix of its login (§3.2)? | Derive it from the login. | **Yes** (maintainer). Derived from the login, no setting. |
| P2 | `includeElements=authInfo` on RRI, which never returns authInfo. | 501 `02102` through `auth_info_readable`, so a client is not told there is none. | **Accepted** (maintainer). |
| P3 | Is the MTEST run a required check for RRI phases, or best effort when an allowlisted machine is at hand? | Required for R3–R7, recorded in the plan. | **Required before merge** (maintainer): coding and review go on without it, the PR leaves draft only after a recorded MTEST pass (§5.4). |
| P4 | The licence of the DENIC XSDs in [docs/rri/xsd/](xsd/). DENIC publishes them openly but states no licence. | Keep them checked in. | **Accepted** (maintainer). |
