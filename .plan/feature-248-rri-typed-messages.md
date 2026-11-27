# Plan: feature/248-rri-typed-messages (#248, closes #132)

Stacked on `feature/183-rri-extension-tree` (PR #253, ready, unmerged). Merge order: #253, then this PR. The spec is done
(commit fd649ee, extension 0.3.0); it is the contract.

## Decisions settled before the plan (maintainer/orchestrator)

- One RPP message type per RRI msgType. `chprovAuthInfo` -> `transferOutcomeMessage` (`serverApproved`, process with the gaining client);
  the TRANSIT notice is `domainReleaseMessage`; `contactDelete` handles all objectType `contact`; Registry Notice = code, text, arguments
  (level dropped); no personal data in messages; anything untranslatable stays a `serviceNoticeMessage`, still readable and acknowledgeable.
- `GET /messages?type=...`: one QUEUE-READ per value that has an RRI msgType, the oldest (msgtime) wins; values without one read nothing
  (only such values: empty queue). `RPP-Queue-Size`: without `type` the untyped msgcnt, with `type` the sum of the msgcnt of the QUEUE-READs sent.
- `DELETE /messages/{id}`: QUEUE-DELETE without msgType; on 63650063607 a QUEUE-READ per msgType finds the type the id heads, then a
  QUEUE-DELETE with it. `GET /messages/{id}` finds the message the same way. An id that heads no type: 404 02303.
- The EPP backend keeps ignoring `type` (EPP Compatibility Profile, core §16.10.1).
- Generic mechanisms of #183 (registered extension, member registries); no RRI names in core, rpp/http, rpp/handlers, generic mappers.
  `rpp:messages` handling is generic. Import-linter contracts hold.
- Extension version references -> 0.3.0; schema copied by copy_models.sh. #132 is superseded: the PR says "Closes #132" and "Closes #248".

## Findings (evidence)

- `registry_adapter/rri/commands/message/queue.py`: every message becomes a text-only QueueMessage ("RRI <kind>: <names>"), `event` None.
  `rpp/mapping/message/messages.py` then renders a service notice. `RriMessageGateway.poll()/ack()` take no type.
- `validate_schema("message.read", rpp)` in `messages.model_to_rpp` passes no extensions, so it validates against the scope of NO extension
  (`RequestSchemas.for_extensions(())`): the mapper needs the extensions of the response preset (`response_profile().extensions`, as the domain
  handlers pass them).
- Bundle `message.read`/`message.create`: `properties.data.oneOf` is a closed list of 6 `$ref`s (json §6.8); `compose()` in
  `rpp/schema/effective_schema.py` only composes `rpp:extends` with `allOf`, so a branch cannot be added that way. `RppExtension`
  (`rpp/schema/rpp_extension.py`) and `_from_schema` (`rpp/schema/extensions.py`) know no `rpp:messages`.
- `type` is `string, explode: false` in `rpp/openapi.yaml` (`gen.message.query.parameters.type`); core §16.10.1 says it MAY be repeated.
- `63650063607` maps today to `OBJECT_DOES_NOT_EXIST` in `registry_adapter/rri/result_codes.py` (404); `ErrorResponse.registry_code` carries the code.
- `core/flows/message/message_flows.read_message` polls the head and compares ids; non-head -> `UNIMPLEMENTED_OPTION` (501).
- Contracts: `rri-common-not-extensions` (common RRI code cannot import `registry_adapter.rri.extensions`, loads it by name through
  `extension_part.py`); `rri-extensions-core-only` (the RRI part of an extension may import `extensions.*.core`, the generated XML and
  `registry_adapter.rri.statuses`, not `rpp`, `core.flows`, `register_rri`); `generic-not-extensions`.
- Integration: `message/test6` expects on RRI a `serviceNoticeMessage` for the `chprovAuthInfo` notice of its transfer; that becomes a
  `transferOutcomeMessage`. DENIC queues notices of its own on MTEST (`env.message.queue.server_notices`) and the run setup drains queues.

## Approach

### 1. Extension point `rpp:messages` (generic, `rpp/schema`)
- `RppExtension.messages: dict[str, str]` (message type identifier -> definition name in `defs`), read by `_from_schema` from `rpp:messages`.
  Refused at registration, naming the extension: a target not in `defs`, an identifier that a base message definition already has
  (`<identifier>.read` in the bundle) or that another registered extension maps.
- `compose()`: after copying the definitions and before the injection, append `{"$ref": "#/$defs/<target>"}` for every mapped
  definition of every extension of the preset to `message.read` and `message.create` `properties.data.oneOf`. So the Effective Schema, the
  Preset Schema (`GET /presets/{id}/schema`), the served OpenAPI documents and the validators carry them; a preset without the extension has none.
- `own_definitions`/`SchemaScope` need no change (`ext.rri.<x>.read` validates as `<x>.read`).
- Copy the schema (`copy_models.sh`); `test_the_mapping_and_the_overview_are_those_of_the_schema` also asserts the `rpp:messages` block of
  the doc; the 4 failing doc examples (valid message.read 8-11) must pass.

### 2. Core model and port (generic)
- `core/model/message/extension_event.py`: `ExtensionEvent(extension_id: str, event: object)` (the event is the typed object of the extension's
  own core); `QueueMessage.event` may be one. `QueueMessage.text` stays the fallback notice text.
- `MessageGateway.poll(client_transaction_id=None, message_types: tuple[str, ...] | None = None)`: `None` = untyped; the identifiers are
  those of RPP message types, which a backend that cannot filter ignores (EPP, SQLite). New `MessageGateway.find(message_id, client_transaction_id=None)`
  -> the response of the message with that id, `None` where the backend can only read the head (EPP, SQLite).
- `core/flows/message/message_flows.py`: `poll_messages(backend, types, ctid)` (thin) and `read_message`: head first; id differs ->
  `backend.messages.find(...)`: a response -> it; `None` -> today's 501; a registry answer "no such id" -> 404 `02303`. Handlers stay thin.

### 3. RPP side (generic)
- `rpp/mapping/message/message_mappers.py`: `MessageMapper` protocol (`extension_id`, `to_rpp(event) -> dict` the `data`, with `@type`) and
  `MESSAGE_MAPPERS` (process-global, idempotent, like `DOMAIN_MEMBERS`).
- `messages.model_to_rpp(message, *, backend_name, extensions)`: an `ExtensionEvent` is rendered by the mapper of its extension when the
  extension is one of the response preset's `extensions`, else (and when validation against `message.read` of that preset fails) a service
  notice, as for any untranslatable message. Handlers pass `response_profile().extensions`.
- `messages_query`: `type` -> list of identifiers (see open question 1), passed to the flow. `RPP-Queue-Size` is the payload's.

### 4. RRI adapter
- Common RRI (`registry_adapter/rri/`): `message_type.py` (`RriMessageType`: msgType, RPP identifier, `translate(element)`), `RriExtensionPart`
  gets `message_types` read from the part module (`MESSAGE_TYPES`, default none), loaded by name like `gateways`.
  `RriMessageGateway(client, parts)` builds its table: the base `chprovAuthInfo` -> `transferOutcomeMessage` (a `TransferEvent`:
  serverApproved, objectType `domainName`, objectId `msg:ace`, request and action date `msgtime`, `DomainTransferProcess` with
  `reqClientId` = `actClientId` = `msg:new`) plus those of the parts. A msgType with no translator stays the text notice.
- `commands/message/queue.py`: `rri_queue_read(client, ctid, msg_type=None)`; the gateway's `poll(types)`: no types -> one untyped read; types
  -> one typed read per value with a msgType, oldest by `msgtime` wins, queue size = sum of `msgcnt`; no value maps -> an empty queue
  (code 1300, size 0, no command sent). `ack`: QUEUE-DELETE without msgType, on `registry_code == 63650063607` the reads per msgType,
  QUEUE-DELETE with the type whose oldest message has the id; none -> the original error mapped to 404 (`02303`). `find(id)`: the same search.
  A QUEUE-DELETE never gets the reply of `63650063607` as 404 to the client where the retry finds the id.
- Extension part `registry_adapter/rri/extensions/rri/messages.py`: `MESSAGE_TYPES` for the 14 types, translating the XML to
  `ExtensionEvent(EXTENSION_ID, <event>)`; imports `extensions.rri.core` and the generated XML and `registry_adapter.rri.statuses` (domain status of
  `domainStatusUpdate`), as the contracts allow.
- Extension core `extensions/rri/core/model/`: `ObjectReference`, `RegistryNotice`, `RriMessageKind`, and the events `BulkMessageEvent` (expiry
  warning, expiry, contact deletion: objects with dates), `NoticeMessageEvent` (kind, object, notices: the 7 notice types), `AuthInfoMessageEvent`
  (expiry date or none), `DomainStatusMessageEvent`, `ContactVerificationMessageEvent`.
- Extension RPP `extensions/rri/rpp/mapping/messages.py` (`RriMessageMapper`, registered in `register_rri.register` like the request contact
  members) renders the events to the `data` of `rri-extension.schema.json`; `RppExtension` version 0.3.0.
- No personal data: only domain names, handles, codes, texts and arguments of notices; warnings logged by code only (existing rule).

### 5. Versions, configuration, docs
- 0.3.0 in `rri-preset.yaml`, `rri-profile.yaml` (src copies of docs 0.3.0 already require it), tests that state 0.2.0 for RRI. No new
  configuration key (process.md rule 5: nothing to propagate).
- `docs/agents/architecture.project.md` (Messages paragraph: `type`, typed events, `rpp:messages`, queue part), `testing.project.md`
  (message/test6 on RRI), `.spec/spec-issues.md` (the line "`type` is ignored" says RRI filters), `docs/rri/gap-analysis.md` (Q15, the notice
  is replaced) as far as they state the old behaviour.

## Tests

- Unit, no network: `tests/unit/rri_replies/` XML replies built from `docs/rri/xsd/message-5.0.xsd` and the examples of the reference §9, one per msgType
  (15), as files; `test_rri_adapter.py` (typed poll, `type` selection by oldest msgtime and the sum of msgcnt, no mapped value sends nothing,
  QUEUE-DELETE retry after 63650063607 with the msgType found, id heading no type, find by id); `test_rri_wire.py`
  (GET `/messages`, `?type=`, `/messages/{id}`, DELETE with the retry, 14 types validate under the `rri` preset, a service notice under `base`).
- `test_rpp_message_mapper.py`/`test_rpp_extensions.py`/`test_effective_schema.py`: `rpp:messages` in the effective schema, refusals at registration,
  the mapper of an extension in an app that has none (notice).
- The 4 doc examples; `test_the_mapping_and_the_overview...` for `rpp:messages`; extension-isolation tests (an app without the extension holds
  no message branch); EPP and SQLite ignore `type`.
- Integration (MTEST): `message/test6` expects the `transferOutcomeMessage` on RRI. Typed messages only where MTEST produces them reliably (the
  chprovAuthInfo of the transfer in test6); a `type=` case for it (`GET /messages?type=transferOutcomeMessage` after the transfer, ack of a
  non-head message by id) if it can be produced deterministically; else unit tests only. Full checks of process.project.md, with the MTEST probe first.

## Tasks

- [x] Plan, approval
- [x] 1. `rpp:messages`: RppExtension, compose, registration checks, copy_models.sh, doc test
- [x] 2. Core model, port, flows, handlers (`type`, `find`, `extensions`), EPP/SQLite signature
- [x] 3. RRI adapter: typed read/delete/find, chprovAuthInfo, extension part, extension core and mapper
- [x] 4. Versions 0.3.0 in code, presets, profile, tests
- [x] 5. Unit tests, replies, wire tests
- [x] 6. Integration cases (test6) and docs (architecture, testing, spec-issues, gap analysis)
- [~] 7. Checks: lint-imports, unit tests, smoke (MTEST probe), PR draft (stacked on #253, Closes #132, Closes #248)

## Decisions of the orchestrator (answers to the open questions)

1. `type`: core §16.1.7 (Rule 7) and §16.10.1 make a repeated parameter normative: accept the repeated form, and also comma-separated
   values (split, empty parts dropped) for clients that follow the generated OpenAPI's `explode: false`. Add a spec-issues entry for that
   contradiction. Test both forms on the wire (Connexion must neither refuse nor mangle the repeated form).
2. `find(id)` on the gateway, `None` where only the head is readable: yes.
3. A message of an extension type under a preset without the extension is a service notice: yes, stated in architecture.project.md.
4. 63650063607 stays 404 outside the ack/find retry: yes.
5. The `model_to_rpp` validation bug (no extensions) is in scope; named in the PR body.

## Open questions (answered above)

1. `type` syntax: OpenAPI has `explode: false` (comma-separated), core §16.10.1 says "MAY be repeated". Recommend: accept both (every
   repeated value split on commas, empty parts dropped), so `type=a,b` and `type=a&type=b` are the same.
2. Reading past the head by id: new gateway method `find(id)` (None for EPP/SQLite) as above, versus a flag on the backend profile. Recommend `find`.
3. An RRI message of an extension type under a preset without the extension (`base` on an RRI deployment) is a service notice (the
   Effective Schema of that preset has no branch for it). Recommend this; it is the fallback the proxy already has.
4. `63650063607` stays mapped to 404 for any other path; the retry swallows it only where the id heads a type.
5. Domain status in `domainStatusMessage.status` is a Domain Name Status Object: `{"@type": "domainNameStatus", ...}` per the doc's example; I take
   the shape from the doc examples (messages section) and the schema, no decision needed unless they differ.

## Results

- MTEST probe (domain_availability/test3): passed, so the smoke run covers MTEST.
- First smoke run on 8cabbef: 231 passed, 2 failed (rri-mtest `preset_read/test1`, `draft_discovery/test1` state the extension version 0.2.0): fixed to 0.3.0.
- `message/test6` (with the new `?type=transferOutcomeMessage` step) is not marked smoke: run on rri-mtest, passed.

## Review round 1 (PR #255, head 9cc6eb4)

Decisions of the orchestrator, all done:
1. An ack whose search read fails answers that error (as `find`), not the original 404. Test added.
2. The test of an event failing its definition is a wire test under the `rri` preset (domainDelete without notices: 200, service notice, the id); the adapter test shows the event with no notices.
3. A `type` value naming a message type of an extension the response preset lacks is dropped before the backend is asked (`message_types_outside`): under `base` `type=domainLockMessage` is an empty queue, nothing sent. Under `rri` a message whose data fails its definition is the service notice and still answered for the requested type (documented deviation, architecture.project.md and spec-issues.md). Both tested.
4. Different msgcnt in the head and found replies of the read-by-id test; the sum of `RPP-Queue-Size` asserted for several values.
5. "planned" dropped from spec-issues.
6. The oldest message is compared in UTC, a time without an offset as UTC (`utc_moment`); tested.
7. `utc_time` used in commands/contact/common.py and commands/domain/common.py.
