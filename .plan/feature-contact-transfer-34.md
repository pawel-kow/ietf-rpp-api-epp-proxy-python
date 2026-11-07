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

## Review round (PR #90)

- Approve reads and validates its body per object kind (`*_transfer_approve`), in the shared handler, so domains change too: `reason` 501 (02102), anything else not allowed 400 (02001), nothing sent to EPP. Raw body is read with `request.body()`, since `get_body()` returns parsed JSON.
- Requests are parsed with request-only classes (`RPPTransferRequest`, `RPPDomainTransferRequest`): a read-only member is 400 (02001) for contacts and domains (json §4.4).
- A success reply without `trnData` is 202 with no body and the `RPP-*` headers, in the shared handler, for both kinds.
- Contact transfer sends `id.upper()`, as create does. Other contact commands are not changed, see the issue filed.
- `authInfo` stays forwarded on query, cancel, approve and reject. RFC 5733 §3.2.4 does not say a server ignores it, so that is not cited.
- The direction guard is `reject_push` in `common.py`. The contact command has its own `_transfer_auth_info`, because the contact and domain `AuthInfoType` are different classes.
- Commit 5302270 holds the domain behaviour change and, necessarily, the contact approve and request classes it wires.

## Review round 2 (PR #90)

- Bodies are read with `flask.request.get_data()`, not `asyncio.run(request.body())`, which hung under uvicorn when the body arrived after the headers. A loopback uvicorn test with a delayed body reproduces the hang on the old code (4 runs hung) and passes now.
- `require_empty_body` (all DELETE routes: contacts, domains, hosts and transfer cancel) rejects any raw body, `{}`, `null`, `[]`, `0`, `false`, `""`, whitespace and `{bad` included, and any form body (`flask.request.form` is needed: without it all 5 form tests fail). Core §16.1.4. This is a wire change for every DELETE.
- Approve with bytes that parse to `null`, or only whitespace, is 400 (02001).
- A query without `trnData` is 500 (02400) with a fixed detail, since it applied nothing. Create, cancel, approve and reject stay 202.
- `contact_transfer/test17` reads `C17`.

## Backend notes

- A completed contact transfer cannot be queried (2301), like #65. Cancel by the non-requester is 2201, also with nothing pending, like #66.

## Open questions

None.
