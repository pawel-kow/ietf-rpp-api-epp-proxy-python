# Contact transfer process (#34)

Base: `main` at 5258d2b. Does not depend on #81, #83, #86 or #88.

## Tasks

- [x] Settle the open questions with the orchestrator
- [x] Failing tests: unit (xml, rpp mapper, wire) and integration `contact_transfer` cases
- [x] Extract the shared transfer handlers from `controller/domain_transfers.py`
- [x] Contact models, EPP command and parser, `epp_contacts_Transfer`, RPP mappers, controller
- [x] Unskip and adapt `draft_contact` test7 to test11
- [x] Update `.spec/spec-issues.md` (Transfer process) and `docs/agents`
- [~] Full `pytest`, draft PR
- [ ] `git rm` this plan, release the mutex on `main`

## Findings

- OpenAPI has `contactTransferProcesses_*` operations; no controller exists, hence 501 (02101).
- RFC 5733 contact transfer has no period; `trnData` has `id`, no `exDate`. Schema `transferProcess.create` allows only `@type`, `transferDir`, `gainingClientId`; `transferProcess.read` has no `expiryDate` or period.
- Domain transfer code (`controller/domain_transfers.py`, mappers, models) is specific to domains in naming only.

## Decisions

Carried over from #33: query with nothing pending 409 (02301); approve takes an empty body or `{"@type": "transferProcess"}`; `reason` 501 (02102); list and `/{processId}` 501 (02101), no `processId` in responses; `transferDir: push` and `gainingClientId` 501 (02102), responses `transferDir: pull`. Any other body member 400 (02001), so `transferPeriod` on a contact is 400.

- Approved by the orchestrator: `TransferHandlers` refactor (own commit), `@type` `transferProcess`, `transferPeriod` on a contact 400 (02001, json §4.4), push 501.
- `draft_contact/test11` keeps the draft's reject body with `reason` and expects 501 (02102); `contact_transfer/test2` rejects without a body.
- Adapted `draft_contact` test7 to test11 with `FO-` ids and real steps.

## Backend notes

- A completed contact transfer cannot be queried (2301), like #65. Cancel by the non-requester is 2201, also with nothing pending, like #66.

## Open questions

None.
