# PATCH: full JSON Patch semantics (#27)

Branch `feature/patch-semantics-27` from `main` b000212. Hybrid, agreed with the maintainer: operations that map to
one EPP add/rem/chg are sent without a read; a patch with any operation that needs the current state reads the
domain (`info`), applies the patch in memory, and sends the difference in one EPP update. The read and the update
are not atomic (accepted). Background and examples: `.spec/spec-issues.md`.

## Tasks

- [x] 1. Maintainer accepts this plan (answers below)
- [x] 2. Patch applier `json_patch.py`, difference `domain_patch_difference.py`, `rpp_to_model_with_current`
- [x] 3. `flows/domains.py`: direct or read path
- [x] 4. EPP update XML: domain status, secDNS update extension, hostAttr with addresses on `rem`, `authInfo` null
- [x] 5. Controller `domainNames_updatePartial` calls the flow
- [x] 6. Tests: unit (applier, difference, flow, XML) and integration cases test8 to test12 and draft_patch test2/test4
- [x] 7. Docs: `architecture.project.md`, `testing.project.md`, `spec-issues.md`
- [~] 8. Full `pytest`; draft PR; before merge `git rm` this file

## Design

- Direct path stays as today (`domain_patch.py`), so the common patch is still one EPP round trip.
- Read path reuses the pattern of `flows/hosts.py::replace_host` (info, `_difference`, update, read back).
- In-memory apply follows json §5.2.2 step by step (array with/without `match`, primitive/object, ambiguous
  `replace` with `match` fails, no match fails). The diff yields `DomainUpdate` add/rem/chg.
- Statuses: only `client*` statuses are diffed, as for hosts (`_client_statuses`).

## Findings

- `domain_patch.py` rejects the operations in task 4 with `reject_operation` (501, `02103`), see
  `common.py:29`. `host_patch.py` has the same limit for hosts; the issue names only `domainNames`.

## Decisions (maintainer)

1. Domains only. Hosts: #71. Contacts: #29 (comment added).
2. No element matches and ambiguous `replace`: `02308` (422), noted in `spec-issues.md`.
3. `/dns` on the read path is covered by unit tests only (#60).
4. Remove `/authInfo` maps to `<domain:null/>`, with no read.

## Findings

- The read-path patch is applied to the read representation, and step 6 validates it with `domainName.read`. A patch that
  leaves `status` empty therefore fails the schema (400); `ok` is server-managed, so `replace /status` with client statuses is the way.
- The wire unit tests take about 1.5 s each, the unit suite several minutes.
