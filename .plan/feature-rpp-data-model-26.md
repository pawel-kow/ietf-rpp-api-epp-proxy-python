# RPP data the internal model cannot hold (#26)

## Decisions (accepted by the maintainer)

- `hostAttr` domains read as `dns` records with their glue, `hostObj` domains as `nameservers`. Glue of a `hostObj` domain stays at `GET /hosts/{name}`, no extra `host:info`.
- `status` on domain and contact create: stays 501 (`02102`).
- `uName` and `lgr`: stay 501, no `uName` computed on read. Follow-up issue: can `idnLang-1.0` cover them?
- `kind: individual` with `organizations`: stays 501.
- #26 closes with this PR. `disclose` gets its own issue, `processes` on read stays with #33, #35, #36. PATCH `/dns` and `/status` stay with #21 and #27.
- Still 501: `dns.controls`, DS and DNSKEY in one request, other record types.

## Findings

- Stale in #26 after #57: `language`, one localization, `name.components` without `full`, `full`-only addresses, `country` component, several addresses or organisations, other phone features.
- Backend returns `roid` and `domain:host`. It never returns `upID` or `upDate`, even after an update.
- Backend accepts secDNS on create and update, but Info returns no `secDNS:infData`.
- Backend accepts `hostAttr`, and stores a `hostObj` and a subordinate host. Info returns no addresses.

## Corrections

- `a`, `aaaa` etc. in upper case were 501 on hosts, but data-objects §9.9 says to convert the type to lowercase. Fixed in the code shared with domains.

## Tasks

- [x] Read metadata: `repositoryId`, `upClientId`, `subordinateHosts`
- [x] DNSSEC on create and read
- [x] Delegation in `dns` on create, `hostAttr` on read
- [x] Docs, spec-issues, skip of `draft_domain/test7-read_idn`
- [~] Full pytest, draft PR, follow-up issues
