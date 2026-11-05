# Domain transfer process (#33)

## Tasks

- [~] Failing tests with stubs
- [ ] `RPP-Authorization` header parsing, `AuthInfo.roid`
- [ ] Models, `domain_transfer_process` and `domain_transfer_reject` mappers
- [ ] EPP `<transfer>` command, `trnData` parsing, `epp_domains_Transfer`
- [ ] Controller handlers for the five `latest` operations
- [ ] Integration cases with `foo` and `baz`, enable draft tests 11-15
- [ ] `spec-issues.md`, GitHub issue for the 409 gap, agent docs
- [ ] Full `pytest` with the live backend
- [ ] File upstream backend defects

## Findings

Probed with a raw EPP client on the live backend (foo sponsors, baz gains).

- `request` answers `1001` with `trnData`, so no follow-up Info.
- Wrong or no authInfo `2202`. Sponsor requesting `2106`. Request while pending `2300`.
- Wrong registrar on cancel, approve or reject `2201`.
- query, approve and cancel with no pending transfer `2301`, also right after a
  transfer completed.
- `exDate` in `trnData` only when a period was requested.
- `RPP-Authorization` is not read anywhere yet.

Backend defects (file as `upstream:epp-server`):

- Info has `ok`, not `pendingTransfer`, during a pending transfer.
- A completed transfer cannot be queried (`2301`).
- After cancel, `acID` is still the losing registrar. After cancel or reject, `acDate`
  stays in the future.

## Decisions

Accepted by the maintainer.

- `GET .../latest` with nothing pending: 409 `02301` per Table 9, with an issue for the
  OpenAPI, which has no 409 there.
- Reject with `reason`: 501 `02102`. Draft test 15 changes from 200.
- List and `/{processId}` stay 501 `02101`. EPP has no process ids or history.
- `1001`: 201 and `Location: .../latest`. `1000`: 200, no `Location` (core §16.3, no
  exposed process resource).
- Push and `gainingClientId`: 501 `02102`.
- Approve accepts a body or none (core and json draft disagree).
- The header's authInfo goes on every transfer operation, not only `request`.

## Open questions

None.
