# Full JSON Patch semantics for hosts (#71)

## Tasks
- [x] Failing tests (unit and integration)
- [x] `json_patch`: parents of known paths may be absent
- [x] Shared status view for hosts and domains
- [x] `host_patch` read path, `patch_host` flow, controller
- [x] Domains: clear statuses, `/dns/records` and `/dns/controls` take the read path
- [x] Docs: architecture, testing, spec-issues
- [~] Full `pytest`, draft PR

## Decisions (maintainer)
- `replace /status []` and `remove /status` clear the client statuses, on hosts and domains, although
  Figure 3 rejects removal of a 1+ property. Goes in spec-issues.md.
- A patch is applied as if server statuses were not on the object. Leaving one out changes nothing.
  Setting one is 400, matching one finds no element (422).
- `ok` stays visible: the draft example replaces it (`draft_patch/test2`).
- Fix the domain `/dns/records` bug here.

## Findings
- `domain_patch.rpp_to_model` answers 400 for `/dns/records` unless an earlier operation took the read path.
- `json_patch` answers 400 for `/dns/records` on an object without `dns`, step 2 allows it.
- Read records carry the old name, so a rename in the same patch must not make them foreign.
- `remove /status` ignores anything in `match` but `label`.
- #71 names `/hostNames` and `02103`. The path is `/hosts`, and the 501 was `02102`.

## Corrections
- The decision replaced what was first proposed: `replace` that omits a server status is not an error either.
- `contact_create/test20` and `domain_create/test17` fail on a clean `main` too.

## Open questions
None.
