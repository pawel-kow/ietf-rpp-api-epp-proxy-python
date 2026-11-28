# Plan: #262 RRI split 2/5, generic authinfo extension

Branch `262-rri-split-authinfo` (holds the approved specification, commit 5a6b1f0). Stacked on `267-backends-declare-extensions`
(#268) -> `261-rri-split-messages` (#266), both unmerged; merge order #266, #268, this. The PR targets main. Mutex taken.
Normative: docs/extensions/authinfo-extension.md, .spec/authinfo-extension.schema.json, docs/rri/rri-extension.md 0.4.0,
rri-preset.md, rri-strict-preset.md, .spec/spec-issues.md, gap-analysis.md.

## Decisions (orchestrator, for the maintainer)

- New package `src/extensions/authinfo/` (register_authinfo.py, core/{model,ports,flows}, rpp/{dto,mapping,handlers,schema}) in the
  structure of messages/domain_lock/registry_changes/rri; schema copy equal to `.spec/authinfo-extension.schema.json`.
  It moves the authinfo parts of `extensions/rri`: model/ports/flows, dto/mapping/handlers, the schema definitions of
  `authInfoProcess`, `authInfoIssueProcess`, the three message types, and the `processes` registration under `domainName`
  incl. `profile_layer` / `profile_leaves` of their operations (leaf names unchanged, so test selectors keep working).
- The extension names no backend (#267). `io.github.pawel-kow.rpp.authinfo` added to `registry_adapter/rri/extensions/__init__.py`
  PARTS; the RRI part (gateways, commands, message types) moves to `registry_adapter/rri/extensions/authinfo/`.
- The generic extension does not import `extensions.rri` (added to `generic-extensions-not-rri`, layers contracts like the
  others). rri imports nothing of it unless needed.
- `de.denic.rpp.rri` stays 0.4.0; its src schema copy is refreshed from `.spec`; rri-preset.yaml adds authinfo 0.1.0 last;
  `config/backends/rri.yaml`, `deploy/ansible/configs/rri-mtest.yaml.j2` and README add `extensions.authinfo` last (process.md
  rule 5). PR body: the maintainer adds `extensions.authinfo` to inventories outside git.
- The dependency check of #261 accepts authinfo (refs to the messages definitions). The generic extension extends the base
  definition `processes.read`; rri keeps its own mapping of it. The Effective Schema must combine both: tested.
- Method check: generic = reject an unsupported method (as `rpp.mapping.shared.auth_info` does today, `NotSupportedByBackend`,
  RRI 501 02102). No wire change: paths, members, @types, codes unchanged; only extension ids in discovery and media-type
  parameters, and the owner of the three message types.

## Approach (coder)

- core: `AuthInfoProcess`, `AuthInfoSetting` (moved), `AuthInfoMessageKind` (three identifiers) and `AuthInfoMessageEvent(kind, object,
  expiry_date, notices)` replacing the rri `AuthInfoMessageEvent` and the withdrawal's `NoticeMessageEvent`; ports of the two
  gateways and `AuthInfoGateways(auth_info_processes, auth_info_issues)`; flows unchanged apart from the extension id.
  `RriGateways` drops both gateways; `RriMessageKind` the three kinds (rri keeps its notice/bulk/status events).
- rpp: dto, mapping (`auth_info_process`, `auth_info_issue_process`, `messages`), handlers (own `gateways()` accessor), the
  OpenAPI fragment for the two processes. The process-path builder of rri's `openapi_fragment.py` (a rename of the domain's
  transfer-process paths) moves to `rpp/schema/process_openapi.py`, used by rri (verification, release) and authinfo, so the
  generic extension does not import rri.
- RRI part: `registry_adapter.rri.extensions.authinfo` (`gateways(client)`, `MESSAGE_TYPES`, the commands moved from `rri/commands/`).
- Finding to fix: `registration.profile_layers.with_extensions` overwrites a top-level key (`domainName`) that two extensions add
  (`extra[key] = value`), so authinfo would drop rri's `generalRequest`, `abuse`, other processes. It becomes a deep merge of the
  dicts, with a unit test (this is the only change outside the moved code, besides the shared OpenAPI builder).
- Tests: authinfo in NAMES/FOLDERS of test_extension_docs.py, in RRI_PROFILE extensions, REPOSITORY_EXTENSIONS, fixtures with the
  rri preset extensions (discovery, preset read, offered presets); the authinfo unit tests keep their cases, with the new
  imports and extension id; a test of the combined Effective Schema for `processes.read`; message tests with the new owner.
- Docs: overview.project.md, architecture.project.md (structure, registered extensions, contracts), testing.project.md:235, README,
  copy_models.sh, pyproject contracts.

## Tasks

- [~] Plan checkpoint (orchestrator approval)
- [ ] Package, schema copy, registration, RRI part, rri slimmed (schema refreshed from .spec, kinds, events, gateways)
- [ ] profile_layers deep merge + test; shared process OpenAPI builder
- [ ] Configs, deploy template, presets, README
- [ ] Tests updated, Effective Schema test, docs, import-linter contracts
- [ ] Checks (lint-imports, unit, smoke, MTEST reachability + smoke incl. authinfo_process cases), draft PR

## Findings

- `with_extensions` (src/registration/profile_layers.py) keeps only the last extension's value for a shared top-level key.
- Both `rpp.mapping.shared.auth_info` (method check) and the process mappers are already generic; only the owner changes.

## Open questions

- None blocking. One recommendation: `AuthInfoMessageEvent` unites the three message types in one event (as `NoticeMessageEvent` did
  for the withdrawal), with `kind` choosing the `@type`.
