# Plan: domain transfer over RRI (CHPROV) — #133

Branch `feature/133-rri-transfer`, from `chores/remove-old-tests` @ ea02f82 (the maintainer's choice: that branch waits
for its integration run), in the worktree `.claude/worktrees/133-rri-transfer`.

## Decisions (maintainer, 2026-11-14)

- **Gap Q3 → option B**: a request extension. The client sends the gaining registrar's data with the transfer request.
- **Body: flat members.** An extension schema (json §7, `rpp:extends`) adds `registrant`, `contacts` and `dns` to
  `domainTransferProcess.create`, with the definitions of `domainName.create`. `registrant` and `dns` are required.
  `nameservers` is not in it (RRI has no host objects).
- **Response: synthesised, no extra command.** CHPROV is immediate and its reply has no transfer state: 200, no
  `Location`, `trStatus` `serverApproved`, `reqClientId` = `actClientId` = the gainer's RegAccId, `requestDate` =
  `actionDate` = the time of the reply, no `expiryDate`.
- **Schema and discovery now.** The extension schema lives in `.spec/rri-extension.schema.json` and is copied by
  `copy_models.sh`; the validator composes the effective schema (allOf) when the `BackendProfile` offers the
  extension; discovery lists it in `extensions`. The extension is described in `.spec/spec-rri-extension.md`, not in
  `spec-issues.md`.
- Query, cancel, approve, reject and push stay 501 on RRI. TRANSIT, CREATE-AUTHINFO2, regacc INFO and NIS2 (Q8–Q10,
  Q16) stay out of scope.

## Design

- Profile: new top-level leaf `extensions` (tuple, the RPP extensions discovery states): `[]` in `epp.yaml`, `[rri]`
  in `rri.yaml`; `rri.yaml` transfer operations `[request]`.
- `rpp/schema`: the extension file carries `$id` (its URL), `rpp:extends`, and `rpp:extension` (name, id, version);
  `validate_schema(name, data, extensions=())` composes the effective schema; an `Extension` list for discovery.
- `domain_transfer_process.rpp_to_model(..., profile=)`: with the extension, validates the effective schema, takes
  `registrant`, `contacts`, `dns` out and converts them with `domains.rpp_to_model` into `DomainTransfer.domain`;
  without it, as today (an undeclared member is 400).
- `core.model.domain.DomainTransfer.domain: Domain | None`: the domain's data after the transfer, for a backend whose
  transfer states it.
- RRI: `rri_domain_chprov` in `commands/domain/update.py` (with UPDATE and CHHOLDER), `RriDomainGateway.transfer` builds the `DomainState` and
  answers the synthesised `DomainTransferProcess`. A request without the AuthInfo is refused before a command
  (`2003`). `53370080005` → `2003`.
- Discovery: `Discovery.extensions`, rendered as `extension.read`.
- Tests: the existing EPP-style transfer cases are gated on `profile.extensions` not containing `rri`; a new group
  `domain_transfer_ext/` of RRI transfer cases (success, wrong AuthInfo, no AuthInfo, missing data, own domain,
  foreign contacts); `domain_transfer/test14` pins the 400 of the members without the extension.
- Extension ids are checked at start (`create_app`). The extension's url is its schema on GitHub (`$id`).

## Tasks

- [x] T1 Plan
- [x] T2 Extension schema, `.spec/spec-rri-extension.md`, copy_models.sh, validator composition (unit tests first)
- [x] T3 Profile leaf `extensions`, rri.yaml transfer `request`
- [x] T4 Mapper + model (`DomainTransfer.domain`), handler passes the profile (unit tests first)
- [x] T5 RRI CHPROV command + gateway + result code (unit tests first)
- [x] T6 Discovery `extensions` (unit tests first)
- [x] T7 Integration cases: gate the EPP transfer group, new RRI transfer cases (`domain_transfer_ext/`)
- [x] T8 Docs: gap-analysis Q3/§4.3, architecture.project.md, testing.project.md, security.project.md
- [~] T9 Checks: lint-imports, `pytest -n 8` (EPP), MTEST run
- [ ] T10 Draft PR

## Findings

- MTEST takes CHPROV on a domain still `pendingCreate` (`domain_transfer_ext/test1`, 2026-11-14).
- A foreign contact in CHPROV is `63200020603` (403 `02201`), the own domain `63380063209` (409 `02002`).
- A domain label longer than the XSD allows (66 characters with the TLD) is an RRI schema failure, 500 (`02400`):
  the group name is part of `{random_name}`, so a group name over about 20 characters breaks RRI cases.

## Open questions
