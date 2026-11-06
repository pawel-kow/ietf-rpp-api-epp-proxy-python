# PATCH: full JSON Patch semantics (#27)

Branch `feature/patch-semantics-27` from `main` b000212. Hybrid, agreed with the maintainer: operations that map to
one EPP add/rem/chg are sent without a read; a patch with any operation that needs the current state reads the
domain (`info`), applies the patch in memory, and sends the difference in one EPP update. The read and the update
are not atomic (accepted). Background and examples: `.spec/spec-issues.md`.

## Tasks

- [~] 1. Maintainer accepts this plan (scope, design, open questions)
- [ ] 2. Domain model of the patch: mapper turns the operations into typed model operations (framework-free)
- [ ] 3. `flows/domains.py`: decide direct or read path; read path = info, apply in memory, difference, update, read back
- [ ] 4. Cover the unsupported operations: whole-array replace/remove, replace with match, partial-match remove,
        `/status`, `/dns`, remove `/authInfo`, "no element matches"
- [ ] 5. Controller `domainNames_updatePartial` calls the flow (only this operation leaves the handler; #17 stays)
- [ ] 6. Tests: unit (mapper, difference, flow with fake client) and integration cases against the backend
- [ ] 7. Docs: `architecture.project.md` (domain_patch paragraph, "Unsupported input"), `spec-issues.md` proxy notes
- [ ] 8. Full `pytest`; draft PR; before merge `git rm` this file

## Design

- Direct path stays as today (`domain_patch.py`), so the common patch is still one EPP round trip.
- Read path reuses the pattern of `flows/hosts.py::replace_host` (info, `_difference`, update, read back).
- In-memory apply follows json §5.2.2 step by step (array with/without `match`, primitive/object, ambiguous
  `replace` with `match` fails, no match fails). The diff yields `DomainUpdate` add/rem/chg.
- Statuses: only `client*` statuses are diffed, as for hosts (`_client_statuses`).

## Findings

- `domain_patch.py` rejects the operations in task 4 with `reject_operation` (501, `02103`), see
  `common.py:29`. `host_patch.py` has the same limit for hosts; the issue names only `domainNames`.

## Open questions

1. Scope: domains only (as the issue says), or hosts too (`host_patch.py`)? Proposal: domains only, hosts a follow-up issue.
2. Error for "no element matches" and an ambiguous `replace`: json §5.2.2 asks for an error that identifies the
   failed operation but defines no result code. Which RPP code and HTTP status do you want?
3. `/dns` in a read-path patch: diff secDNS `dsData` and `hostAttr` from `info`? The backend does not return
   `secDNS:infData` (#60), so integration tests cannot cover it, unit tests only. Acceptable?
4. Remove `/authInfo`: EPP `<domain:chg><domain:authInfo><domain:null/>` is allowed by RFC 5731, but registries
   often reject it. Map it and let the registry answer?
