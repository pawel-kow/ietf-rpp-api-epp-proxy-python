# Domain renew process (#32)

Base: `main` at 5258d2b. Independent of PRs #81, #83 and #86 as far as the plan shows.

## Tasks

- [~] Settle the open questions with the maintainer
- [ ] Failing tests first: unit (mapper, XML, wire) and integration (`domain_renew/`), unskip `draft_domain/test10-renew`
- [ ] `DomainRenew` and `DomainRenewProcess` models, `renew` EPP command XML, `renData` parser, `epp_domains_Renew`
- [ ] `rpp_to_model_mapper/domain_renew_process.py` (`rpp_to_model`, `model_to_rpp`), `RPPDomainRenewProcess`
- [ ] Flow `renew_domain` in `flows/domains.py`, controller handler `domainNameRenewProcesses_renewCreate`
- [ ] `.spec/spec-issues.md` "Renew process", `architecture.project.md`, `testing.project.md`
- [ ] Full `pytest`, draft PR
- [ ] `git rm` this plan, release the mutex on `main`

## Findings

- Only two operations exist: `domainNameRenewProcesses_list` (GET, no EPP mapping, 501 `02101` by absence of a controller) and `domainNameRenewProcesses_renewCreate` (POST).
- `renewProcess.create`: `@type`, optional `expiryDate` (current expiry, date-time), optional `renewalPeriod` (`period.create`, `y`/`m`, 1..99). Response `renewProcess.read`: `expiryDate` is the new one.
- EPP `domain:renew` (RFC 5731 §3.2.3): `curExpDate` is required and an `xs:date`; `period` optional with units `y`/`m` (same as RPP). The reply `renData` has `name` and `exDate`, no period, no process id.
- `RenewType` and `RenData` are already generated; `CommandType.renew` exists.
- RPP expiryDate is optional (data-objects §10.3) while EPP curExpDate is required.

## Decisions

(none yet)

## Open questions

1. Absent `expiryDate`: read the domain (Info) for `exDate` and use its date, or 501?
2. Present `expiryDate`: EPP carries a date only; the time of day has no element.
3. Response: `expiryDate` only (no `renewalPeriod`, no `processId`, no Location). 200 or 201? The OpenAPI POST has both; core §16.9.4 pairs 201 with Location "if the server exposes the process resource", and the draft example test10 expects 201. Transfers answer 200 when EPP exposes no process (core §16.1.4).
