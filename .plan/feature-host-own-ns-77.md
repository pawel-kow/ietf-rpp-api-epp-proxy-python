# Host: own ns record (#77)

Base: `main` at e961421, which includes #73.

## Tasks

- [x] Settle the open questions with the maintainer
- [x] Failing unit tests for each rule
- [x] Drop the own `ns` record on `add`, create and PUT, without a read
- [x] Reject a removal of the own `ns` record
- [x] Reject a create or PUT without the own `ns` record, also with no `dns`
- [x] A read always gives the own `ns` record
- [x] Update the integration cases that create or update hosts without it
- [x] Update `.spec/spec-issues.md` and `docs/agents`
- [~] Full `pytest`, draft PR, maintainer acceptance
- [ ] `git rm` this plan, release the mutex on `main`

## Decisions (maintainer)

- The own `ns` record is dropped from EPP processing, with no read path for it.
- Any attempt to remove it raises.
- A create or update without it raises, including one with no `dns` at all.
- The spec issue asks whether this behaviour is intended or acceptable.

## Findings

- `host.create` and `host.update` require only `@type` and `hostName`, and data-objects §13.2 gives `dns` cardinality 0-1. §13.3.2 says IP addresses MAY be omitted for an external host. Rejecting a create with no `dns` goes beyond the draft.
- `hosts.model_to_rpp` emits no `dns` for a host without addresses (`_dns_to_rpp`, `test_host_without_addresses_has_no_dns`).
- A lone `add` of the record gives an empty update, and the backend answers `2003` (400), as `host_update/test5` and `test15` do.

## Decisions on the open questions (maintainer)

1. Removal: 501 (`02102`). Missing on create or PUT: 400 (`02001`), after the other checks of the request.
2. A patch whose end state lacks the record is a removal, including `remove /dns`.
3. A host without addresses reads back with its own `ns` record.
4. A patch with only `add` of the record answers the backend's `2003` (400).
