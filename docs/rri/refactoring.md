# Refactoring for RRI as a second backend protocol

This document proposes how to restructure the proxy so that it can speak DENIC RRI 5.0 to the registry, as an
alternative to EPP. The RPP API stays the same. Which RRI transaction serves which RPP operation, and where they
do not fit, is in [gap-analysis.md](gap-analysis.md). The RRI facts are in [rri-5.0-reference.md](rri-5.0-reference.md).

Status: **proposal, for acceptance.** Under [process.md](../agents/process.md) rule 2 and the working agreement in
[AGENTS.md](../../AGENTS.md), nothing here is implemented until the maintainer accepts it. The open questions in
[gap-analysis.md §7](gap-analysis.md#7-open-questions) must be answered first, and Q20 (the wire format) in
particular.

**Prerequisite:** the split of full and partial updates (§3.5) is a refactoring of its own, tracked as
[issue #108](https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/issues/108) ("Keep full and partial updates apart down to the model"). It changes no EPP behaviour and must be merged before phase 1 (§6).

## 1. Goals and non-goals

Goals:

- One deployment talks to **one** backend, EPP or RRI, chosen in configuration. The RPP wire contract (paths,
  schemas, the §18.1 code → status mapping, the `RPP-*` headers) is unchanged.
- Controllers, flows and the RPP mappers are written once, against a protocol-neutral **backend port**. Rules 3–6
  of [architecture.md](../agents/architecture.md) apply: no second copy of an orchestration, and dependencies
  point downward.
- The EPP behaviour stays exactly as it is. The first phases are pure refactorings, and the existing test suite
  proves them.

Non-goals:

- Running EPP and RRI side by side in one process, or routing by TLD.
- Exposing RRI-only functions (AuthInfo2, TRANSIT, regacc INFO, NIS2 verification) in the first version. See Q8,
  Q9, Q10 and Q16.
- The RRI K/V format, unless Q20 decides otherwise.

## 2. Where the code is bound to EPP today

| Place | Binding | Evidence |
|---|---|---|
| Composition | `run.py` builds `EPPClient(TCPClient(...))` and hands the factory to `EppSessionAuthenticator`. | [run.py](../../src/run.py) |
| Session | The authenticator keeps one `EPPClient` per user. The token info key is `epp_client`, and controllers read it through `get_epp_client()`. | [epp_session_authenticator.py](../../src/controller/epp_session_authenticator.py), [auth.py](../../src/controller/auth.py) |
| Controllers | They call `epp_domains_*`, `epp_contacts_*`, `epp_hosts_*` and `epp_messages_*` directly (two with `import *`), and `raise_epp_error` for errors. | [controller/domains.py](../../src/controller/domains.py), [contacts.py](../../src/controller/contacts.py), [hosts.py](../../src/controller/hosts.py), [messages.py](../../src/controller/messages.py), [transfer_handlers.py](../../src/controller/transfer_handlers.py) and the two `*_transfers.py` |
| Flows | They import `eppclient.epp_*` and type their argument as `EPPClient`. `require_sponsor` compares the sponsor with `epp_client.username`. | [flows/](../../src/flows/), [sponsor.py](../../src/flows/sponsor.py) |
| Update model | `DomainUpdate`, `ContactUpdate` and `HostUpdate` are EPP add/remove/change deltas. **Both** PUT and PATCH end as such a delta before they reach the flow, so the full update is turned into EPP's partial one inside the neutral layers. The difference is computed in three places, at two levels. For domains it is computed on RPP representations, in the RPP mapper. For contacts it is computed on models, also in the RPP mapper. For hosts it is computed on models, in the flow. | [models/domains.py](../../src/models/domains.py), [flows/domains.py](../../src/flows/domains.py), [flows/hosts.py](../../src/flows/hosts.py), [domain_patch_difference.py](../../src/rpp_to_model_mapper/domain_patch_difference.py), [domain_replacement.py](../../src/rpp_to_model_mapper/domain_replacement.py), [contact_difference.py](../../src/rpp_to_model_mapper/contact_difference.py) |
| RPP mappers | They decide what the *backend* can hold: `NotSupportedByEpp` is used in 12 modules, there are EPP contact labels (`CONTACT_LABELS`), the apex records EPP cannot hold, and what EPP cannot clear on a contact. | [not_supported_by_epp.py](../../src/rpp_to_model_mapper/not_supported_by_epp.py), [domains.py](../../src/rpp_to_model_mapper/domains.py), [domain_dns.py](../../src/rpp_to_model_mapper/domain_dns.py) |
| IDN | `IdnTables` maps `lgr` to an EPP IDN-extension table. | [idn_tables.py](../../src/rpp_to_model_mapper/idn_tables.py) |
| Models | `NS` is `hostObj`/`hostAttr`, `AuthInfo` is `pw`/`roid`, `ContactReference.types` holds EPP roles, and `QueueMessage.event` is `TransferEvent \| PendingActionEvent` (EPP `trnData`/`panData`). | [models/](../../src/models/) |
| Result codes | `ResultCode` holds the EPP codes. An RPP code is the EPP code with a leading `0` (core §18), so this stays the internal code space. Only the RRI adapter needs a translation, see §3.8. | [models/response.py](../../src/models/response.py), [rpp_response.py](../../src/controller/helper/rpp_response.py) |
| Transport | `TCPClient` writes `len(payload) + 4` (RFC 5734 counts the header). RRI counts the payload only. `EPPClient.connect` reads a greeting, and RRI sends none. | [tcpclient.py](../../src/eppclient/tcpclient.py), [eppclient.py](../../src/eppclient/eppclient.py) |
| Configuration | `rpp_epp_*` keys only. | [config.py](../../src/config.py) |
| Discovery | `OBJECTS` (including `host`) and `PROFILES` (`epp-compatibility`) are constants. | [controller/discovery.py](../../src/controller/discovery.py) |
| Tests | `FakeEppClient` replays EPP XML at `send_and_get_response`. 24 test files touch the EPP client. | [tests/helper/fake_epp_client.py](../../tests/helper/fake_epp_client.py) |

## 3. Target design

```
openapi.yaml
   │
controller/        thin handlers: RPP request → mapper → flow/backend → RPP response
   │  ├── rpp_to_model_mapper/   RPP JSON ↔ models, capability checks via the injected BackendProfile
   │  └── flows/                 multi-step orchestration, protocol-neutral
   │
registry/          the backend port: protocols and value types, no I/O     ← new
   │
   ├── eppclient/ + epp_to_model_mapper/      EPP adapter (existing code, behind the port)
   └── rriclient/ + rri_to_model_mapper/      RRI adapter                  ← new
models/            provider-neutral domain model (widened, §3.6)
```

### 3.1 The backend port

There is a new package, `registry/`, with one class per file. It contains only `typing.Protocol` definitions and
small value types. It imports `models` and nothing else:

- `RegistryBackend`, the session object a request works with:
  - `domains: DomainGateway`, `contacts: ContactGateway`, `hosts: HostGateway`, `messages: MessageGateway`.
  - `profile: BackendProfile`, the static capabilities (§3.7).
  - `sponsor_id: str`, the registrar id the registry stores as sponsor (EPP: the login; RRI: the RegAccId, see
    gap Q17).
- `DomainGateway`: `check`, `info(name, auth_info=None)`, `create`, `update(delta, current=None)` (partial),
  `replace(wanted, current=None)` (full), `delete`, `transfer`, `renew`, `restore`. §3.5 explains why the port
  keeps partial and full updates apart. The signatures and return types are those of today's `epp_domains_*`: a typed
  `*Response` or an `ErrorResponse`, without exceptions for registry errors. The one difference is the
  `client_transaction_id` keyword. A method the backend lacks returns
  `ErrorResponse(UNIMPLEMENTED_COMMAND, …)`, so `raise_epp_error` (to be renamed `raise_registry_error`) renders
  it as 501 `02101`.
- `ContactGateway`, `HostGateway` and `MessageGateway` follow the same shape (`poll`, `ack`).

The EPP adapter (`eppclient/epp_backend.py`) wraps today's functions one to one. `EPPClient` stays the EPP
session. No EPP behaviour changes, so the unit and integration tests carry over unchanged.

**Why a gateway rather than a new set of flows for RRI.** The commands an RRI update needs (UPDATE or
CHHOLDER, plus AuthInfo commands, §3.5) translate one neutral request, either a partial or a full update. They
belong in the adapter, like the EPP XML building. The flows stay single: read when the RPP layer needs the
current state, update or replace, read back. A flow passes `current` when it has already read the object, so no
backend reads twice.

### 3.2 Session and authentication

- `EppSessionAuthenticator` becomes `SessionAuthenticator`. Its logic is protocol-neutral already: a factory,
  one session per user, `connect`/`connected`/`verify_credentials`. The token key `epp_client` becomes
  `backend`, and `get_epp_client()` becomes `get_backend()`.
- `RriClient` (in `rriclient/rriclient.py`) has the same session contract as `EPPClient`:
  - It sends a LOGIN with `user` and `password`, with no greeting first, and LOGOUT on disconnect.
  - It serialises the exchanges with a re-entrant lock, as `EPPClient` does.
  - On a dead socket it reconnects and logs in again, and it retries **only** if the command was never written.
    RRI writes are not idempotent, and a CTID cannot be reused (ref §3.3).
  - It refreshes an idle session before the 5-minute timeout, by reconnecting on demand. The alternative is a
    `QUEUE-READ`, which costs no quota but is a read the client did not ask for, so this proposal avoids it.
- Login throttling is out of scope for now. The lockout it would prevent is listed as a risk in §7.

### 3.3 RRI wire format

**XML 5.0** is the recommendation (gap Q20):

- The server validates XML strictly against the XSDs. K/V *silently ignores unknown keywords* (ref §3.1). Under
  RRI's full-replacement update, a misspelt K/V keyword deletes stored data without an error. That breaks the
  proxy rule that nothing is dropped silently.
- The DENIC XSDs (global, transaction, domain, dnsentry, contact, message, regacc, verification) can be compiled
  with xsdata into `rri_to_model_mapper/rri_model/`, as `epp_model/` is generated today. The generated code is
  exempt from the one-class-per-file rule, as `epp_model/` is.
- Responses are parsed with the same hardened `decode_xml` (no entities, no DTD).

To do: get the XSDs from the DENIC member site ("Schemata and BNFs"). Check their licence before checking them
in; until then, generate them in the build.

### 3.4 Transport

- `TCPClient` takes a `framing` argument: the length counts the header (EPP, RFC 5734) or not (RRI). The
  EPP default does not change. `tests/unit/test_tcpclient.py` covers both.
- The greeting parse moves out of the transport path into `EPPClient` (where it already lives). The RRI client
  does not read one.
- The TLS context is reused: verification on by default, and the `insecure_skip_verify` switch for test backends
  only. The certificate is DENIC's public chain, so no client certificate is needed.
- Limits: requests of 64 KB at most, and responses read with the same exact-length loop.

### 3.5 Full and partial update as separate paths

This step is a **prerequisite**, tracked as [issue #108](https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/issues/108) ("Keep full and partial updates apart down to the model"). It is done on the EPP-only code before
phase 1 (§6). Until the port exists, the derivation of §3.5.2 sits in one EPP-side module, which phase 1 moves to
`registry/derived_update.py`.

The two protocols make opposite choices:

- **EPP has only partial updates.** `<update>` carries add, remove and change, and nothing else.
- **RRI has only full updates.** UPDATE and CHHOLDER replace the object, and an omitted optional value is
  deleted (gap §4.1).

Today the neutral layers turn every RPP update into an EPP delta (§2). On RRI the delta would have to be turned
back into a full state. So the proposal keeps the client's intent, **partial** or **full**, all the way down to
the model and the port. Each backend implements its own kind natively. The other kind is derived from it once,
in shared code.

#### 3.5.1 Two request types in the model

| Intent | Model type | Meaning | Produced by |
|---|---|---|---|
| Partial | `DomainUpdate` (as today: `add`/`remove`/`change`) | Only the named changes. Everything else stays. | A PATCH that maps without the current state (`domain_patch.rpp_to_model`) |
| Full | `DomainReplacement` (**new**) | The wanted state of every replaceable member. An omitted member is cleared. | A PUT (`domain_replacement.rpp_to_model`), and a PATCH that needs the current state (§3.5.3) |

`DomainReplacement` holds:

- only the members a client may replace: `registrant`(s), `contacts`, `nameservers`, `dns` and the client
  statuses with their reasons;
- `auth_info` as an explicit intent: `KEEP`, `SET(pw)` or `CLEAR`. A PUT without `authInfo` is `KEEP`, as
  [spec-issues.md](../../.spec/spec-issues.md#full-update-of-a-domain) decides today. A PATCH `remove /authInfo`
  is `CLEAR`.

Read-only members (`provMetadata`, server statuses, `subordinateHosts`) are not part of it. So a PUT no longer
needs the read representation in order to keep them. That is what
`domain_replacement.rpp_to_model_with_current` does now.

The same applies to contacts (`ContactUpdate` and a new `ContactReplacement`) and to hosts (`HostUpdate` and a
new `HostReplacement`, which is EPP only).

#### 3.5.2 Native and derived per backend

The port has both methods: `update(delta, current=None)` and `replace(wanted, current=None)`.

| | EPP adapter | RRI adapter |
|---|---|---|
| `update(delta)` | **Native**: one `<update>`. No read. | **Derived**: read (unless `current` is given), `wanted = apply(current, delta)`, then native `replace` |
| `replace(wanted)` | **Derived**: read (unless `current` is given), `delta = difference(current, wanted)`, then native `update` | **Native**: UPDATE or CHHOLDER with the full state, plus AuthInfo commands. A read is still needed to pick the command and to carry data over (below). |

The two conversions are pure functions on the model, written once:

- `difference(current: Domain, wanted: DomainReplacement) -> DomainUpdate` is today's
  `domain_patch_difference.difference`. It moves from RPP dictionaries to models, see §3.5.4.
- `apply(current: Domain, delta: DomainUpdate) -> DomainReplacement` is new.

The derivation itself is one orchestration: read if needed, convert, call the native method. It sits in one
module, `registry/derived_update.py`, which both adapters call. Rule 6 of
[architecture.md](../agents/architecture.md) forbids a hand-written copy in each adapter.

Backend-specific refusals stay in the adapter that has them. `difference` produces a neutral delta that can
include "clear" intents. The **EPP** adapter refuses the ones EPP cannot clear (`NotSupportedByBackend`), as
`contact_difference.py` does today. The RRI adapter needs no such check, because a full update clears by
omission.

The native RRI `replace` for a domain:

1. Read `current` if it was not given. The read decides three things: whether the holders change (CHHOLDER or
   UPDATE), whether an AuthInfo1 exists (DELETE-AUTHINFO1 before CREATE-AUTHINFO1), and whether anything changes
   at all.
2. If nothing differs and `auth_info` is `KEEP`, send no command and return "unchanged" (§3.5.3).
3. If the holders differ → CHHOLDER(wanted). Otherwise, if anything else differs → UPDATE(wanted).
4. `SET(pw)` → DELETE-AUTHINFO1 if one exists, then CREATE-AUTHINFO1(sha256(pw)). `CLEAR` → DELETE-AUTHINFO1 if
   one exists. After a CHHOLDER both are skipped, because it already removed all AuthInfos.
5. Return the response of the last command, or a partial-failure result (gap Q7).

For a contact, step 3 is one UPDATE. The adapter also copies the verification blocks from `current` into the
request, because RPP cannot carry them and leaving them out deletes them (gap §4.5).

#### 3.5.3 Flows after the split

| RPP request | Flow | EPP commands | RRI commands |
|---|---|---|---|
| PATCH that maps directly | `backend.update(delta)` → read back | update, info (2) | INFO, UPDATE, [AuthInfo], INFO (3+) |
| PATCH that needs the current state | read → JSON Patch on the read representation → `DomainReplacement` → `backend.replace(wanted, current)` → read back | info, update, info (3) | INFO, UPDATE, [AuthInfo], INFO (3+) |
| PUT | `backend.replace(wanted)` → read back | info, update, info (3), as today | INFO, UPDATE, [AuthInfo], INFO (3+) |

- For a PATCH that needs the current state, the result becomes a wanted state, not a delta.
  `domain_patch.rpp_to_model_with_current` stops after the JSON Patch has been applied (json §5.2.2). It maps the
  patched representation to a `DomainReplacement`, and it no longer calls the difference. EPP derives the delta
  in its adapter, and RRI uses the wanted state as it is. The read the flow already made is passed as
  `current`, so neither backend reads twice.
- For a PUT, the flow does not read. The backend reads, because both backends need the current state for a full
  update: EPP to compute the difference, RRI to pick the command. The flow has no reason to read for its own
  sake.
- **A request that changes nothing** sends no command, as today. Today `patch_domain` and `replace_domain`
  find this out from an empty delta. After the split, `replace` returns a result marked `unchanged`, together with
  the `current` it read. The flow then runs `require_sponsor` with it (`flows/sponsor.py`), so the 403 for a
  non-sponsor stays where it is. On RRI this also avoids sending an UPDATE that only repeats the stored data.
- The read-back after a mutation, and its 202 when the read-back fails, stay in the flows and work the same for
  both backends.
- `flows/hosts.py` loses `_difference`. That becomes `difference(current: Host, wanted: HostReplacement)` in the
  model, called by the EPP adapter. `replace_host` and `patch_host` take the same shape as the domain flows.

#### 3.5.4 Cost and risk of the split

- **The domain difference moves from RPP dictionaries to models.** `domain_patch_difference.py` compares two RPP
  representations today, and its behaviour is pinned by `test_rpp_domain_patch_current_mapper.py` and
  `test_rpp_domain_replacement_mapper.py`. The model must keep what the difference depends on:
  - `nameservers` (`hostObj`) kept apart from `ns` records with glue (`hostAttr`), and refused together;
  - a status whose reason changed, sent as a remove and an add;
  - per-host address changes of glue records;
  - the refusal of changes to members outside `CHANGEABLE`.

  `Domain.ns` with `host_objs` and `host_attrs`, and `status_reasons`, hold all of this already. The tests move
  to model level with the same cases.
- **`apply` is new code.** It is pinned by round-trip tests: for every delta the EPP mappers can produce,
  `difference(current, apply(current, delta))` must equal `delta`, up to order.
- **EPP behaviour does not change.** The EPP commands of every request stay the same, so the integration suite
  proves the split (§5). This happens in the prerequisite issue, before any RRI code exists.
- **Contacts**: `contact_difference.py` already works on models. It moves to `models/` as the neutral
  `difference`. Its EPP checks (what EPP cannot clear, `with_stored_localization`) go to the EPP adapter.

#### 3.5.5 Other RRI flows

- **Create with authInfo**: `create` on RRI is CREATE, then CREATE-AUTHINFO1 in the adapter. The handler keeps its
  read-back and its 202 rule.
- **The domain transfer** follows gap Q3. Under option C the RRI `transfer()` returns `UNIMPLEMENTED_COMMAND`.
- **Renew** on RRI: `renew()` returns `UNIMPLEMENTED_COMMAND`. `renew_domain` reads `exDate` first when no
  `expiryDate` was given, which would be a wasted INFO. So the flow asks `profile.supports_renew` first.
- **Messages**: `read_message` is protocol-neutral already: poll, then compare ids. RRI's `msgcnt` fills
  `queue_size`.

### 3.6 Models

The model must hold what either backend holds. Changes, each with its own tests:

| Model | Change |
|---|---|
| `DomainReplacement`, `ContactReplacement`, `HostReplacement` | New: the full-update request with an explicit `auth_info` intent (§3.5.1). One file each. |
| `difference`, `apply` | New neutral conversions between the full and the partial request (§3.5.2): `models/domain_difference.py`, `models/domain_application.py`, and the same for contacts and hosts. |
| `Domain.contacts` / `ContactReference.types` | Neutral role names (`registrant`, `admin`, `tech`, `billing`, `generalRequest`, `abuse`), and several `registrant`s allowed (gap Q1). |
| `Domain` DNS | Add apex and subdomain `a`/`aaaa`/`mx` records (RRI `Nsentry`). `NS` stays: RRI name servers are `HostAttr` (`hostObj` is never used on RRI). |
| `DnsSec` | RRI uses `key_data` only. No change. |
| `Domain` status | Neutral labels already (`ok`, `pendingCreate`, `serverHold` …). Add `status_due` next to `status_reasons` for the `failed` deadline. |
| `Domain` read | `authInfo` absent on RRI. `crDate` absent when RRI gives `before …`. |
| `Contact` | `email` already a list. Phone exactly one on RRI (checked by the profile). Add `verification: list[...]` as opaque carry-over data, which is never rendered to RPP. |
| `QueueMessage.event` | Add a neutral `ServiceNoticeEvent` and an `ExpirationEvent`. `TransferEvent` gains an optional source so the RRI `chprovAuthInfo` fits. |
| `ResultCode` | Unchanged. `ErrorResponse` gains an optional `registry_code: str` (the 11-digit DENIC code) for the detail and the logs. |

The known-debt rule applies: `models/domains.py` holds 17 classes (#20). New model classes go into files of their
own, and the debt must not grow.

### 3.7 Mappers and capability checks

The RPP mappers now decide two things: whether RPP input is valid, and whether EPP can hold it. The second
question moves behind an injected **`BackendProfile`**, passed the way `IdnTables` is passed today
(`create_app` → `app.config` → handler → mapper):

- `NotSupportedByEpp(feature)` becomes `NotSupportedByBackend(feature, backend_name)`, with code `02102` as now.
  For EPP the message text stays `… cannot be expressed in EPP`, so the existing assertions hold.
- `BackendProfile` holds the facts the mappers check:
  - `contact_labels`: EPP `admin`/`billing`/`tech`; RRI `generalRequest`/`abuse`.
  - `max_registrants`: EPP 1; RRI 5.
  - `domain_record_types`: EPP `ns` (+glue), `ds`, `dnskey`; RRI `ns` (+glue), `a`, `aaaa`, `mx`, `dnskey`.
  - `host_objects`: EPP yes; RRI no.
  - `client_statuses`: EPP yes; RRI no.
  - `contact_fax`, `contact_localization`, `contact_region`: EPP yes; RRI no.
  - `contact_phones_max`.
  - `supports_renew`, `supports_contact_delete`, `supports_transfer_query`.
  - `objects` (for discovery) and `profiles`.
- `IdnTables` stays EPP-specific. On RRI, the profile accepts no `lgr`, or one configured name (gap Q11), and
  sends `uName` as the RRI `Domain`.
- What a backend cannot *clear* is backend logic, and moves into the adapter (§3.5.2). The neutral difference
  goes to `models/`, and the refusal of what EPP cannot clear goes to the EPP adapter. On RRI nothing needs
  clearing, because the update replaces the whole object.
- The RPP mappers stop computing differences. `domain_replacement`, `domain_patch.rpp_to_model_with_current`,
  `contact_replacement`, `contact_patch.rpp_to_model_with_current` and `host_patch.rpp_to_model_with_current`
  return a `*Replacement`. `domain_patch.rpp_to_model` and `contact_patch.rpp_to_model` still return a delta, or
  `None` when the current state is needed. See
  [architecture.project.md](../agents/architecture.project.md#unsupported-input) for the three kinds of
  unsupported input, which stay as they are.

### 3.8 Result codes and errors

- `rri_to_model_mapper/result_codes.py` holds the DENIC code → `ResultCode` table and the class-digit fallback in
  [gap-analysis.md §5](gap-analysis.md#5-result-code-mapping). It is one table, unit-tested code by code.
- `raise_epp_error` becomes `raise_registry_error`. Nothing else changes: it maps `ResultCode` through core
  §18.1. When there is a DENIC code, the detail starts with it.
- A `success` with warning or error messages (predelegation warnings, deadline infos) is logged with its codes,
  never its arguments, because they can hold personal data
  ([security.project.md](../agents/security.project.md)).

### 3.9 Configuration and composition

New keys, with all existing `rpp_epp_*` keys unchanged:

```yaml
rpp_backend: epp                 # epp | rri, default epp
rpp_rri_host: rri.test.denic.de
rpp_rri_port: 51131
rpp_rri_use_tls: true
rpp_rri_tls_insecure_skip_verify: false
rpp_rri_timeout: 5
rpp_rri_regacc_id: DENIC-1000022 # the sponsor id, gap Q17
rpp_rri_lgr: null                # gap Q11
```

`run.py` remains the single composition root. It reads `rpp_backend`, builds the client factory and the
`BackendProfile` for it, and passes both to `SessionAuthenticator` and `create_app`. There is no `if backend ==`
anywhere else.

### 3.10 Discovery

`OBJECTS` and `PROFILES` come from the `BackendProfile`. On RRI they are `["domainName", "contact"]` and a profile
to be decided. The EPP Compatibility Profile does not describe RRI, so it needs its own URN or a spec issue.

## 4. Package layout

Existing packages stay where they are, to keep the diff small and the history readable. New packages:

```
src/registry/                    port: registry_backend.py, domain_gateway.py, contact_gateway.py,
                                 host_gateway.py, message_gateway.py, backend_profile.py,
                                 derived_update.py (the one derivation of §3.5.2)
src/models/                      + domain_replacement.py, contact_replacement.py, host_replacement.py,
                                 auth_info_intent.py, domain_difference.py, domain_application.py, …
src/eppclient/epp_backend.py     EPP adapter over epp_domains_* etc.
src/rriclient/                   rriclient.py (session), rri_backend.py (adapter),
                                 rri_domains.py, rri_contacts.py, rri_messages.py
src/rri_to_model_mapper/         request building and response parsing, result_codes.py,
                                 statuses.py, rri_model/ (generated from the DENIC XSDs)
tests/helper/fake_rri_client.py  replays RRI XML, like fake_epp_client.py
```

This is a new top-level structure, so it needs the maintainer's confirmation (process rule 2).

## 5. Testing

- **The EPP suite is the safety net for the prerequisite and phases 1–3.** It must pass unchanged, both the unit tests and the
  integration tests against the devcontainer EPP server
  ([testing.project.md](../agents/testing.project.md)).
- **RRI unit tests** use `FakeRriClient` with XML replies taken from the DENIC examples (`EX:` pages, ref §0), one
  per transaction and per error class. They cover the update composition (UPDATE vs CHHOLDER, AuthInfo
  sequences, carrying verification blocks over) and the result-code table.
- **RRI integration tests** need the DENIC test environment: a membership, an allowlisted IPv4 and `rri.test.denic.de`.
  The devcontainer has none of these. Options:
  - a local RRI stub server, a counterpart of the EPP test server, which behaves like the DENIC test system
    for the cases in `test_case_data`;
  - a manual or CI job against DENIC test, with credentials kept outside the repository.
  The data-driven suite `test_from_file_definition.py` assumes EPP behaviour (hosts, transfers, renew), so the
  RRI run needs its own case set, or skips by backend profile.

## 6. Migration plan

One PR per phase, each following [process.md](../agents/process.md), with a branch, a `.plan/` file and the full
`pytest` run. The prerequisite and phases 1–3 change no behaviour.

| Phase | Content | Behaviour change |
|---|---|---|
| 0 | **Prerequisite**, [issue #108](https://github.com/pawel-kow/ietf-rpp-api-epp-proxy-python/issues/108) ("Keep full and partial updates apart down to the model"): split full and partial updates (§3.5). Add the `*Replacement` types. Move the differences to `models/`, the domain one from RPP dictionaries to models. Add `apply`. EPP gets `replace` as a derived method. The commands sent to EPP stay the same. | None |
| 1 | Add the `registry/` port and the EPP adapter. Move the derivation of phase 0 to `registry/derived_update.py`. Controllers and flows call `get_backend()`. Rename the authenticator and `raise_registry_error`. | None |
| 2 | Add `BackendProfile`, inject it, and rename `NotSupportedByEpp` → `NotSupportedByBackend` with the same texts for EPP. Move the EPP-only checks behind the profile. Discovery reads it. | None |
| 3 | Add `TCPClient` framing. Widen the models as in §3.6, with the EPP mapping unchanged. | None |
| 4 | Add `rriclient` with session, framing, LOGIN/LOGOUT, CTID rules, the result-code table and `FakeRriClient`. | New backend, off by default |
| 5 | RRI domains: CHECK, INFO, CREATE (+AuthInfo1), UPDATE/CHHOLDER, DELETE, and RESTORE per gap Q6. | RRI only |
| 6 | RRI contacts: CHECK, INFO, CREATE, UPDATE (with verification carried over). | RRI only |
| 7 | RRI messages: QUEUE-READ/DELETE and the type mapping. | RRI only |
| 8 | Transfer per gap Q3, and anything decided for Q8–Q10 and Q16. | RRI only |
| 9 | Docs: `architecture.project.md` (the request lifecycle gains the port and the adapters), `testing.project.md` (the RRI backend), `security.project.md` (RRI credentials, the login lockout risk), `overview.project.md`, and the README. | — |

## 7. Risks

| Risk | Mitigation |
|---|---|
| A full-replacement update loses data the proxy did not read or does not know. | XML with strict XSDs. Carry over unknown and NIS2 data. Unit tests that INFO → UPDATE round-trips every field. |
| Read and write are not atomic, so a concurrent change between them is lost. | Same as the EPP path today (`architecture.project.md`). Document it, and map `53000000012` to a retryable status. |
| Moving the domain difference from RPP dictionaries to models changes EPP behaviour unnoticed. | Done on its own as the prerequisite (phase 0). The mapper tests move to model level with the same cases. The `apply`/`difference` round-trip tests and the EPP integration suite run unchanged (§3.5.4). |
| Multi-command requests partly fail. | Gap Q7. Tests for every split point. |
| Anyone with network access can lock the registrar out of RRI with bad logins. After 10 failed LOGINs DENIC blocks the user for an hour, and every HTTP Basic attempt with a wrong password for a username without a session costs a LOGIN. | **Not addressed for now.** Accepted as a known risk. A later step could add a per-username failure counter with back-off that answers 401 locally ([security.md](../agents/security.md)). |
| Writes are non-idempotent, so a retry after a timeout duplicates or fails. | Never retry a command that was written. CTIDs unique per command. |
| Quota and ACL use grows, because a PATCH costs 3–4 requests. | Count requests per RPP operation in the tests. Read-backs stay optional (202 on failure). |
| NIS2 verification is not reachable through RPP, so domains end in `serverHold`. | State it in discovery and the README. Gap Q16. |
| The DENIC docs contain errors (ref §0.3). | The XSDs and recorded real responses are authoritative. Mark each doc-based assumption in the tests. |
