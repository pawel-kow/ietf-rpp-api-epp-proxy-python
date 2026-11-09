# Plan: Restore process (#35)

Branch `feature/35-restore-process`.

## Tasks

- [x] Unit tests first (mapper, XML, wire), with stubs
- [x] Models: `DomainRestore`, `RestoreReport`, `DomainRestoreProcess`, `DomainRestoreResponse`
- [x] `rpp_to_model_mapper/domain_restore_process.py`: create, update (PUT), patch, read
- [x] EPP: `domain_restore` command, `parse_domain_restore_response`, `epp_domains_Restore`, rgp in `LOGIN_EXTENSIONS`
- [x] Flows: `read_domain_restore` (request and report are one command each, no flow)
- [x] Handlers: `domainNameRestoreProcesses_create`, `_read`, `_update`, `_updatePartial`
- [x] Integration cases `domain_restore/`
- [x] Docs: spec-issues "Restore process", architecture.project.md, testing.project.md
- [x] Follow-up issue: RGP state in the domain `status` (#105)
- [~] Full pytest run (2008 passed, 8 skipped), PR

## Decisions (maintainer, 2026-11-09)

1. POST is 200 without `Location` and without `processId`, as renew (core §16.1.4).
2. POST with an inline `restoreReport`: EPP has no single-step restore, so 501 (`02102`). Not emulated with two commands.
3. A report missing a member RFC 3915 requires (`preData`, `postData`, `deleteTime`, `restoreTime`, `restoreReason`, exactly two `statements`) is 400 (`02001`).
4. GET `latest` is a domain Info: `pendingRestore` -> `pendingRestore`, `pendingDelete` -> `rgpPendingDelete`, anything else 404 (`02303`). `restored` is never read, EPP cannot tell it from a domain never deleted.
5. Hosts: EPP has no host restore and the OpenAPI no host restore path, so nothing is added (the path answers 404).
6. List and `{processId}`: 501 (`02101`), no handler.
7. Response of create/report: `restoreStatus` from `rgp:upData` when sent, else `pendingRestore` after a request, `restored` after a report with 1000, `pendingRestore` with 1001. No dates (EPP has none).
8. PATCH applies the JSON Patch to `{"@type": "restoreProcess"}` without a read, then validates `restoreProcess.update`.
9. rgp-1.0 joins `LOGIN_EXTENSIONS`; a server without it gives 501 (`02103`).

## Findings

- Backend greeting offers `urn:ietf:params:xml:ns:rgp-1.0`. Logged in with it, domain Info carries `rgp:infData`; parsing unaffected (probed).
- Backend: restore request on an active domain is `2304`; a delete inside the add grace period purges the domain (`1001`, then `2303`).
- Backend add grace period is 5 days (pawel-kow/epp `command-delete.cgi`, `change-domain-status.pl`); EPP-server-docker shortens only `TRANSFER_WAITING_MINUTES`. Probed: still `addPeriod` after 75 s, and the delete purged the domain. So draft_domain test16, test18, test19 stay skipped.
- `rpp_to_model_mapper/date_time.py` now holds the RFC 3339 check that renew had privately, shared with the report.

## Open questions

- Filing an EPP-server-docker issue for configurable RGP periods was refused by the permission classifier: maintainer to decide.
