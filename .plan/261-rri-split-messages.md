# Plan: #261 RRI split 1/5, generic message extensions

Branch `261-rri-split-messages` (holds the approved specification, commit 51404f7). Mutex taken.
The specification is normative: docs/extensions/{messages,domain-lock,registry-changes}-extension.md, their .spec schemas,
docs/rri/rri-extension.md 0.4.0, rri-preset.md, rri-strict-preset.md, rri-profile.md, .spec/spec-issues.md.

## Decisions (orchestrator, for the maintainer)

- Three new packages `src/extensions/{messages,domain_lock,registry_changes}/` in the structure of `extensions/rri`
  (`register_<name>.py`, `rpp/`, `core/`), each with its schema copy equal to `.spec`; their RRI parts in
  `src/registry_adapter/rri/extensions/<name>/`. The RRI queue-to-message mapping of lock, unlock, update and deletion moves
  from the rri package into the RRI part of the owning extension.
- `de.denic.rpp.rri` 0.4.0 (src schema copy equal to `.spec`; rri-profile.yaml requires 0.4.0; rri-preset.yaml lists rri 0.4.0
  and the three new extensions 0.1.0).
- `config/backends/rri.yaml` `rpp_extensions` lists all four; every configuration and deployment template that states it is
  updated (process.md rule 5).
- Dependency check: implicit, from `#/$defs/<name>` refs in an extension's schema that name a definition of another
  extension. A preset that offers an extension without the ones it depends on is refused at startup in
  `OfferedPresets._offer`, naming both. Unit-tested.
- Wire contract unchanged except extension identifiers in discovery and media-type parameters.
- Tests: messages added to the extension set of test_rri_extension_doc.py; a doc test for docs/extensions/*-extension.md;
  "Checked examples" in specification.project.md; overview and architecture docs that list extensions.
- Generic extensions do not import `extensions.rri`; rri may depend on messages. lint-imports contracts stay green, with
  contracts for the new packages.

## Approach (coder)

- messages: `core/model/{object_reference,registry_notice}.py` (moved from rri), `rpp/mapping/components.py` (the Object
  Reference / Dated Object Reference / Registry Notice dicts), no message type, no mapper. RRI part
  `registry_adapter.rri.extensions.messages`: no gateways, helpers (`_notices`, domain/contact references) shared by the RRI
  parts of the dependents.
- domain_lock: event `DomainLockEvent(kind, object, notices)`, mapper for `domainLockMessage` / `domainUnlockMessage`, RRI part
  `MESSAGE_TYPES` for `lockCreate` / `lockDelete`.
- registry_changes: events for the notice messages (domain update, contact update, domain deletion) and the contact deletion
  (bulk); mapper; RRI part for `domainUpdate`, `contactUpdate`, `domainDelete`, `contactDelete`.
- rri: drops those kinds, events and mapping; imports ObjectReference / RegistryNotice from messages; keeps the rest.
- `RriExtensionPart.gateways` becomes optional (an extension with message types only has none); `RriBackend` skips it.
- `rpp/schema/extension_dependencies.py`: the refs of an extension's defs to another extension's definitions; used in
  `OfferedPresets._offer`.
- Tests that name the extension id of the events (test_rri_messages, helpers `RRI_EXTENSION`, `REPOSITORY_EXTENSIONS`,
  discovery/preset fixtures with 0.3.0) are updated; copy_models.sh copies the new schemas.

## Tasks

- [x] Plan checkpoint (approved)
- [x] Packages, schemas copies, registration, RRI parts, rri slimmed, 0.4.0
- [x] Dependency check in OfferedPresets + unit tests
- [x] Configs and deploy templates, preset/profile yamls
- [x] Doc test for docs/extensions, test updates, docs (overview, architecture, specification.project.md)
- [x] import-linter contracts
- [x] Checks, draft PR
- [~] Review rounds, finish

## Decisions of the orchestrator (after the plan)

- Open question 1: only `messages` is a dependency; a preset with rri but without domain-lock or registry-changes is valid and
  those notifications fall back to service notices. The rri preset includes both. One unit test covers the fallback
  (`test_a_notification_of_an_extension_the_response_preset_lacks_is_a_service_notice`).
- Open question 2: order rri, messages, domain-lock, registry-changes everywhere.
- Issue #203 (an extension without objects needs a backend part): not fixed here. This change does not affect it: `messages`
  has an RRI part without gateways (only `RriExtensionPart.gateways` became optional), because `load_registry` still
  requires a part in the backend for every extension.

## Checks (commit of the PR, no edits during the runs)

- `PYTHONPATH=src lint-imports`: 39 contracts kept, 0 broken.
- `pytest -n 4 tests/unit`: 3431 passed.
- MTEST reachability (`rri-mtest domain_availability test3`): passed, so the smoke run covers rri-mtest.
- `pytest -n 4 -m smoke tests/integration`: 251 passed, 581 skipped (rri-mtest `message::test1-query_head` passes).

## Findings

- `RegisteredExtension` requires a backend part for every extension of a deployment (`registry_setup.load_registry`), so the
  messages extension gets an RRI part although it has no gateways.
- The events carry `ExtensionEvent(extension_id)`; a lock message now has the id of domain-lock. A preset with rri but without
  domain-lock sends a lock notification as a service notice (existing behaviour for an extension that the preset lacks).

## Open questions

1. A preset that holds `rri` without `registry-changes` or `domain-lock` is valid (only `messages` is a dependency); those
   notifications are then service notices. Recommend: accept.
2. Order in `rpp_extensions` and in the preset: messages, domain-lock, registry-changes, rri (discovery order follows the preset
   list). Recommend: the order of docs/rri/rri-preset.md (rri first, then the three).
