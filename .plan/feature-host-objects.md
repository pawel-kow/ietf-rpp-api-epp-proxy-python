# feature/host-objects

Host objects (#31): the `/hosts` operations that have an EPP counterpart.

## Tasks
- [~] Probe mutating host behaviour on the backend
- [ ] Failing tests: unit and integration (`host_*`, `draft_host/`)
- [ ] Models, EPP commands and parsers, eppclient
- [ ] RPP models and mappers, including PATCH
- [ ] `src/flows/hosts.py` and `controller/hosts.py`
- [ ] Docs and `.spec/spec-issues.md`
- [ ] Full pytest run, draft PR

## Decisions (maintainer, 2026-11-04)
- In scope: create, read, delete, availability GET/HEAD, PATCH, PUT.
- Stay 501: host transfer processes (RFC 5732 defines none, goes to spec-issues), `/hosts/{hostName}/processes` (#36).
- New package `src/flows/` holds the mutate-then-Info flow, because it cannot go in handlers (#17). Domain and contact flows stay as they are.
- `dns.records`: an `ns` record is accepted only as the self-reference and emitted on read, following the §8.3.3 example. A/AAAA records must be self-referencing too. Anything else is 501 (`02102`).
- `dns.controls` is 501 (`02102`), so the §8.3.2 example answers 501 as written. Spec issue.
- `status` on create is 501 (`02102`), `host:create` has none. Spec issue.
- A failed readback after a mutation answers 202 with no body, as for domains.

## Findings
- Backend greets with `host-1.0`. `host:check` returns the name uppercased, `host:info` on a missing host is `2303`.
- A reused clTRID hangs the session.

## Open questions
None.
