# Domain renew process (#32)

Base: `main` at 5258d2b. Independent of PRs #81, #83 and #86 as far as the plan shows.

## Tasks

- [x] Settle the open questions with the maintainer
- [x] Failing tests first: unit (mapper, XML, wire) and integration (`domain_renew/`), unskip `draft_domain/test10-renew`
- [x] `DomainRenew` and `DomainRenewProcess` models, `renew` EPP command XML, `renData` parser, `epp_domains_Renew`
- [x] `rpp_to_model_mapper/domain_renew_process.py` (`rpp_to_model`, `model_to_rpp`), `RPPDomainRenewProcess`
- [x] Flow `renew_domain` in `flows/domains.py`, controller handler `domainNameRenewProcesses_renewCreate`
- [x] `.spec/spec-issues.md` "Renew process", `architecture.project.md`, `testing.project.md`
- [~] Full `pytest`, draft PR
- [ ] `git rm` this plan, release the mutex on `main`

## Findings

- Only two operations exist: `domainNameRenewProcesses_list` (GET, no EPP mapping, 501 `02101` by absence of a controller) and `domainNameRenewProcesses_renewCreate` (POST).
- `renewProcess.create`: `@type`, optional `expiryDate` (current expiry, date-time), optional `renewalPeriod` (`period.create`, `y`/`m`, 1..99). Response `renewProcess.read`: `expiryDate` is the new one.
- EPP `domain:renew` (RFC 5731 §3.2.3): `curExpDate` is required and an `xs:date`; `period` optional with units `y`/`m` (same as RPP). The reply `renData` has `name` and `exDate`, no period, no process id.
- `RenewType` and `RenData` are already generated; `CommandType.renew` exists.
- RPP expiryDate is optional (data-objects §10.3) while EPP curExpDate is required.

## Decisions (orchestrator, for the maintainer)

1. `expiryDate` absent: read the domain (Info) and use the date of `exDate`. Not atomic, the client gave up the guard, a retry after a lost response renews twice. Info error is passed through, nothing is renewed.
2. `expiryDate` present: send its UTC date (offset converted), do not reject a non-midnight time. A mismatch is EPP's error (2306, 422).
3. Response 200 (core §16.1.4), no Location, no processId, body validated against `renewProcess.read`. `draft_domain/test10-renew` now expects 200.
4. `1001` is a 200 with `01001`. No `period` in EPP when `renewalPeriod` is absent, no default invented.
5. A `1000` without `renData` gives the body with `@type` only (valid against `renewProcess.read`).

## Findings from the build

- The backend refuses a renew period under one year (`2306`, "not under 1 year and not over 10"), also for months, so integration cases use 12m.
- A wrong `curExpDate` is `2306` on the backend, 422.
- `jsonschema` does not check `format`, so the mapper rejects an `expiryDate` without an offset itself.
