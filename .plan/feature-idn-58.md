# feature/idn-58: IDN on domains (#58)

Map `uName` and `lgr` of a domain to the EPP IDN extension `urn:ietf:params:xml:ns:idn-1.0`
(draft-obispo-epp-idn-04), which the backend implements since pawel-kow/epp@16a4f49 (pawel-kow/epp#26).

## Findings

- The greeting offers `urn:ietf:params:xml:ns:idn-1.0` (probed 2026-11-09). An info of `xn--bcher-kva.example`
  answers `2303`, no longer `2306`.
- draft-obispo-epp-idn-04: `<idn:data>` with `<idn:table>` (required) and `<idn:uname>` (optional) in the
  `domain:create` extension and in the `domain:info` reply. Nothing on check, update, renew, transfer.
- Backend (`EPP/IDN.pm`): an `xn--` name without `idn:data` is `2003`. `idn:data` on an ASCII name, an unknown
  table, a code point outside the table, a `uname` not in NFC or not mapping to the name are `2306`. Without
  `uname` it derives it, so info always returns it. Its tables are `de` and `es` (migration `001_idn.sql`).
- An IDN table id (`de`) is not an LGR name from the IANA IDN tables registry (`latn-1.0`), which json §6.4 asks for.
- Today `GET/HEAD /domainNames/{name}/availability` ignores the `uName` and `lgr` query parameters.

## Decisions (maintainer, 2026-11-09)

1. `lgr` ↔ `idn:table` through a configured map `rpp_idn_lgr_tables` (LGR name → table id, one to one).
   - Create with an `lgr` not in the map: 400. A table not in the map on read: `uName` and `lgr` left out
     (json §6.4 does not allow `uName` without `lgr`), and a warning is logged.
   - No map configured: every `lgr` is a 400, and reads leave both out.
2. `uName` without `lgr` on create: 400 (json §6.4). `lgr` alone goes as `table` alone.
3. Availability with a `uName` or `lgr` parameter: 501 `02102`. An `xn--` name without them is checked as before.

Further:
- The server does not offer `idn-1.0` and the create has IDN data: 501 `02103`.
- Name, table and NFC checks are the server's. Its `2003`/`2306` pass through §18.1.
- PUT and PATCH do not change: `uName` and `lgr` are outside `domainName.update`.

## Tasks

- [~] Plan, branch, mutex
- [ ] `epp_model/idn_1_0.py` (xsdata 25.7 from the draft's schema), `IDN_EXTENSION` in `LOGIN_EXTENSIONS`
- [ ] `DomainIdn` model, `Domain.idn`
- [ ] Failing unit tests: mapper create/read, `IdnTables`, XML create/info, wire 501s, availability parameters
- [ ] Implement: `IdnTables`, config key, `create_app` wiring, mappers, `epp_domains_Create` check, availability
- [ ] Integration: un-skip `draft_domain/test7-read_idn` (create first), `domain_create` IDN cases
- [ ] Docs: architecture.project.md, testing.project.md, spec-issues.md (IDN), config.yaml comment
- [ ] Full `pytest`, PR, close #58

## Open questions

None.
