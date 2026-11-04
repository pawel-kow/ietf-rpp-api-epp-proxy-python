# feature/host-objects

Host objects (#31): the `/hosts` operations that have an EPP counterpart.

## Tasks
- [x] Probe mutating host behaviour on the backend
- [x] Failing tests: unit and integration (`host_*`, `draft_host/`)
- [x] Models, EPP commands and parsers, eppclient
- [x] RPP models and mappers, including PATCH
- [x] `src/flows/hosts.py` and `controller/hosts.py`
- [x] Docs and `.spec/spec-issues.md`
- [x] Full pytest run
- [~] Draft PR, maintainer acceptance

## Decisions (maintainer, 2026-11-04)
- In scope: create, read, delete, availability GET/HEAD, PATCH, PUT.
- Stay 501: host transfer processes (RFC 5732 defines none, goes to spec-issues), `/hosts/{hostName}/processes` (#36).
- New package `src/flows/` holds the mutate-then-Info flow, because it cannot go in handlers (#17). Domain and contact flows stay as they are.
- `dns.records`: an `ns` record is accepted only as the self-reference and emitted on read, following the §8.3.3 example. A/AAAA records must be self-referencing too. Anything else is 501 (`02102`).
- `dns.controls` is 501 (`02102`), so the §8.3.2 example answers 501 as written. Spec issue.
- `status` on create is 501 (`02102`), `host:create` has none. Spec issue.
- PUT clears what the request omits (core §16.8), so an omitted `dns` removes the addresses and an omitted `status` removes the client statuses.
- `add` on `/hostName` acts as `replace` (json §5.2).
- `reason` on a status is 501 (`02102`): read cannot return it. To be confirmed in the PR.
- A failed readback after a mutation answers 202 with no body, as for domains.

## Findings
- Backend greets with `host-1.0`. `host:check` returns the name uppercased, `host:info` on a missing host is `2303`.
- A reused clTRID hangs the session.
- Create with or without addresses works for an external host. Internal needs the domain, else `2303`.
- Addresses come back with a malformed `ip` attribute (`v`, `vv4`), so the parser classifies them by value.
- `host:rem` of an address set at create is `1000` but the address stays. Adding an address the host already has hangs.
- `clientDeleteProhibited` does not stop a delete. `clientUpdateProhibited` gives `2304`.
- Rename works, keeping the roid. Rename out of the superordinate domain is `2005`. Empty update is `2003`, linked delete is `2305`, duplicate is `2302`.
- Addresses given when creating an external host are dropped silently.
- `host:check` on a taken host: `avail="0"`, reason `In use`.

## Corrections
- Empty PATCH is `02001` from the OpenAPI validation, it never reaches the backend.
- Backend defects filed as #49, #50, #51, #52. `draft_host/test5-update` and `host_delete/test4-delete_prohibited` are skipped on them.

## Open questions
None.
