# Domain transfer process (#33)

## Tasks

- [x] Failing tests with stubs
- [x] `RPP-Authorization` header parsing, `AuthInfo.roid`
- [x] Models, `domain_transfer_process` and `domain_transfer_reject` mappers
- [x] EPP `<transfer>` command, `trnData` parsing, `epp_domains_Transfer`
- [x] Controller handlers for the five `latest` operations
- [x] Integration cases with `foo` and `baz`, enable draft tests 11-15
- [x] `spec-issues.md`, GitHub issue for the 409 gap, agent docs
- [x] Full `pytest` with the live backend: 634 passed, 19 skipped (baseline 554, 24)
- [~] Maintainer review of the draft PR
- [x] File upstream backend defects

## Findings

Probed with a raw EPP client on the live backend (foo sponsors, baz gains).

- `request` answers `1001` with `trnData`, so no follow-up Info.
- Wrong or no authInfo `2202`. Sponsor requesting `2106`. Request while pending `2300`.
- Wrong registrar on cancel, approve or reject `2201`.
- query, approve and reject with no pending transfer `2301`, query also right after a
  transfer completed. Cancel with no pending transfer is `2201`, not `2301`: the backend
  checks the requester first, so `tests/unit` pins the 409 of cancel, not the integration
  suite.
- `exDate` in `trnData` only when a period was requested.
- `RPP-Authorization` is not read anywhere yet.

Backend defects, filed as #64, #65, #66 and #67:

- Info has `ok`, not `pendingTransfer`, during a pending transfer.
- A completed transfer cannot be queried (`2301`).
- Cancel with nothing pending answers `2201`, not `2301`.
- After cancel, `acID` is still the losing registrar. After cancel or reject, `acDate`
  stays in the future.

## Decisions

Accepted by the maintainer.

- `GET .../latest` with nothing pending: 409 `02301` per Table 9, with an issue for the
  OpenAPI, which has no 409 there.
- Reject with `reason`: 501 `02102`. Draft test 15 changes from 200.
- List and `/{processId}` stay 501 `02101`. EPP has no process ids or history.
- `1001`: 201 and `Location: .../latest`. `1000`: 200, no `Location` (core §16.1.4, no
  exposed process resource).
- Push and `gainingClientId`: 501 `02102`.
- Connexion rejects an absent optional body, so `RppRequestBodyValidator` allows it.
- Approve accepts a body or none (core and json draft disagree).
- The header's authInfo goes on every transfer operation, not only `request`.

## Open questions

None.
