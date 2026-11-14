# Plan: review of field coverage and probes of backend limits (#136)

Branch `feature/136-limit-probes` from `main` at 414a86e.

## Tasks

- [x] T1 Review of the integration suite per data object field: `docs/testing/integration-test-review.md`
- [x] T2 Limits of the EPP test server and RRI MTEST: `docs/testing/backend-limits.yaml`
- [x] T3 Correction (maintainer): FQDN lengths are defined by DNS (RFC 1035 §2.3.4), not a gap
- [x] T4 Runner: `{pad:N:TEXT}` for a name or id of an exact length (unit tests first)
- [x] T5 Probe cases `limits_domain/`, `limits_contact/`, `limits_host/`, with environment facts for the limits
      that differ by server
- [x] T6 Run on epp-docker (needs `.env`), record the outcomes, file the confirmed defects, mark them `skip`
- [x] T7 Open boundaries of the drafts into `.spec/spec-issues.md`
- [x] T8 Docs: `testing.project.md` (placeholder, facts, the new groups, the EPP test server's limit defects); review
      §6 and §7 with the implemented cases and outcomes; `probe` and `verified` per backend in backend-limits.yaml
- [x] T9 Checks: `lint-imports`, `pytest -n 8` and the MTEST run `RPP_TEST_ENV=rri-mtest pytest -n 4 tests/integration`
- [x] T10 Draft PR #142
- [x] T11 MTEST outcomes into the cases, backend-limits.yaml and review §6
- [x] T12 Correction (maintainer, 2026-11-14): the gaps left in review §3 and §4 get cases in this issue, not a
      follow-up. Domain: create-only members by PATCH, client status at create, `status.due`, registrant and contacts
      added, `dns` transitions (`ns` by PATCH, `a`/`aaaa`/`mx`/`dnskey` on RRI, DS added and removed), clearing
      `contacts` and `nameservers`, duplicates, references that do not exist, `authInfo` absent and removed,
      read-only members written, DNSKEY and record count on RRI
- [x] T13 Contact gaps: `language`, street lines, region, postcode, extension and fax transitions, `disclose` at
      create, client status at create and `replace []`, missing members, value formats, `org-1`, two components of a
      kind, unknown JSContact property, `version`, localization key, phone features
- [x] T14 Host gaps: rename of an external host, status one for another, `aaaa` and `a` by PUT, clearing addresses,
      another record type, upper case and character set of the name, unknown status, `provMetadata` read
- [x] T15 Run on epp-docker and MTEST, file the confirmed defects, mark them `skip`
- [x] T16 Review §1 to §4 and §7 with every case (the `limits_*` ones and the new ones), recounted; testing.project.md
      for any new fact
- [~] T17 Checks, PR body
- [x] T18 Correction (maintainer, 2026-11-14): the facts as a tree, `<object>.<field>.<leaf>` and
      `<object>.processes.<process>.<leaf>`, selector keys with dots, objects and fields by their RPP names. Leaves
      mean the same everywhere: `min_length`/`max_length`, `min_count`/`max_count`, `<what>_supported` rather than
      `<what>_refused`; server defects under `bugs`, with the issue in a comment. Block style YAML, no `{}`
- [x] T19 `BackendProfile` as the same tree, out of Python into YAML: a generic profile per protocol
      (`profiles/epp.yaml` from the EPP Compatibility Profile and RFC 5730–5733, 5910, 3915, gaps commented;
      `profiles/rri.yaml`) and one per server that extends it (`profiles/epp-test-server.yaml`), named by
      `rpp_backend_profile` in the app config. The proxy and the test runner read it from there. The environment
      descriptor loses `profile` and `lgrs`, and the facts `tld` and `environment_name`: they come from the app config
- [x] T20 No failed login with a test account: `wrong_password` and `failed_logins_lock` go, the cases use
      `unknown_user` only, and they run on MTEST too
- [x] T21 Docs (testing.project.md, architecture.project.md, review, backend-limits.yaml), checks on both backends

## Findings (evidence)

6. Profile fields only the test selectors read: `contact_name_changeable`, `supports_contact_delete`,
   `domain_dns_required`, `contact_phone_required`, `registrant_required`. `host_objects` repeats `"host" in objects`.


1. No case tests a value at or over a limit; no array is filled to its maximum (review §2).
2. EPP test server (container `epptest-epp-server-1`, read-only): MariaDB `sql_mode` has no `STRICT_*`, so values
   over a column are cut; `domain.name` is varchar(68); nameservers, contacts per role and host addresses are counted
   per command, not per object (`command-update.cgi`); `secdns.digest` varchar(64) leaves out digest type 4.
3. RRI XSD failures (`83000000004`) and class-5 codes map to 500 `02400` in `registry_adapter/rri/result_codes.py`.
4. The proxy answers more registrants than `profile.max_registrants` with 501 (`rpp/mapping/domain/domains.py:43`).
5. `tests/integration/test_domain_create.py` and `test_domain_delete.py` collect no test.

## Decisions

- D8 (maintainer, 2026-11-14) Facts as a tree with dots; RPP names for objects and fields; the profile in YAML in two
  levels (protocol, server), read by the proxy from the app config; `tld`, `environment_name` and the LGRs from the
  app config; name and email removal is told apart by `profile.contact.<field>.removable` (EPP false: the proxy
  answers 501) and `env.contact.<field>.min_count` (1: the registry refuses).
- D9 Presence is `min_count` for every field, a single value included (`postcode.min_count`), as for name and email.
- D10 The profile is one class, `BackendProfile`, over the tree; its keys and types are a table in
  `core/capabilities/backend_profile.py`, checked when it is built, so a profile file with a missing or unknown key
  stops the app. The layers are merged there (maps merge, lists and values replace), for the config and for tests.

- D7 (maintainer, 2026-11-14) No case accepts a success and a refusal at once. Where the backends decide
  differently, one case each, selected by an `env` fact of server policy; where one backend runs a case, its answer is
  pinned. Also applied to `domain_create/test16` and `test17` from `main`.

- D1 (maintainer) Files in `docs/testing/`.
- D2 (maintainer) Implement the probes; file the confirmed defects; add the open boundaries to spec-issues.
- D3 A probe expects what the drafts say. Where they leave a limit to the server, a value over it is expected to be
  refused with 400 (`02001`, `02004`, `02005`) or 422 (`02306`), as `any_of`; 501 and 500 are not a refusal of a
  limit.
- D4 Limits that differ by server are environment facts (`limit_*`), so a case selects by the limit, not by the
  backend.
- D5 A case whose server cuts a value instead of refusing it (`env.values_cut_at_column`) does not run there; the
  defect is an issue.
- D6 Dropped from the proposal: a label of 1 (no unique name possible), `uName` valid in IDNA2003 only, 21 RRI
  records (another limit is hit first), a request over 64 KiB, a dot in a contact id, a city with a digit, a postcode of 17 (only the EPP test server limits it, and it
  cuts it), an organisation over 255.

## Results

- 90 cases: 30 run on both backends, 37 on EPP only, 23 on RRI only. Unit tests: 1991 passed.
- `lint-imports`: 15 contracts kept (after `pip install -r requirements-dev.txt`).
- `pytest -n 8` on epp-docker: 2357 passed, 38 skipped (5 min 55 s).
- The first run failed 4 cases on contact ids shared with `contact_transfer` (the backend compares ids case-blind):
  the limits cases now use the suffixes `X`, `Y`, `Z`, `Q`, `W`, which no other case uses.
- Confirmed and filed: pawel-kow/epp#29 (limits counted per command), pawel-kow/epp#30 (label of 61 to 63 cut, no
  reply), pawel-kow/epp#31 (extension clamped), #137 (IPv6 not RFC 5952), #138 (label over 63 reaches the registry).
  Read in the code and filed, pending MTEST: #139 (RRI limit refusals are 500), #140 (six holders are 501).
  #141 (dead test modules). Skipped cases name their issue.

- MTEST (2026-11-12): first run 11 of the limits cases failed. #139 and #140 confirmed, those cases skipped.
  `test31` (RRI takes an `aaaa` alone) and `test37`/`test38` (a DNSKEY needs `ns` records, not an `a` record) fixed;
  `test20` skipped (one REQUEST handle on MTEST). Then the full suite: 151 passed, 253 skipped. Limits on epp-docker
  after the change: 60 passed, 30 skipped.

- Gap cases (2026-11-14): 109 cases (domain_create 32–42, domain_update 38–69, limits_domain 53–58, contact_create
  21–41, contact_update 36–60, limits_contact 27, host_create 13–15, host_update 38–46, host_get 4). Integration suite
  now 511 cases: 170 on both, 284 EPP only, 32 RRI only, 25 skipped. Review §2: 379 ✅, 31 ◐, 10 ❌ (dropped, §6.4).
- Filed: #143 (PATCH refused for the `due` of a server status, MTEST), pawel-kow/epp#32 (contact twice in a role: no
  reply), pawel-kow/epp#33 (`hostAttr` without addresses refused).
- MTEST: a DNSKEY must be a valid key, at most 5 a domain (probed); an update with name servers that do not serve the
  zone is refused (`53300102912`), so `ns`/`dnskey` changes are asserted as refusals there; an address needs a
  postcode (new fact `contact_postcode_required`).
- Checks: `lint-imports` 15 kept; `pytest -n 8` on epp-docker 2444 passed, 59 skipped; MTEST integration 202 passed,
  310 skipped (host_create/test15 added after the runs, passed on epp-docker).
- `.env` of this checkout has `TEST_EPP_REGACC2_PREFIX=BA-`, the backend wants `BZ-`: the runs set it in the
  environment. Only `domain_create/test38` and `test42` create a contact as registrar `b`.

- D7 applied: 18 cases pinned or split (4 twins, contact_create/test42–45), 7 server policy facts in both
  environments. `pytest -n 8` on epp-docker: 2445 passed, 63 skipped; the reworked cases pass on MTEST.

- T18–T20: 358 case files renamed by a script (keys only; negated where `_refused` became `_supported`); the four
  name/email removal cases select by `profile.contact.<field>.removable`, then `env.contact.<field>.min_count`. The
  generic profiles are `src/settings/profiles/{epp,rri}.yaml`; `config.yaml` and `config.rri-mtest.yaml` extend them
  with nothing of their own yet. 4 failed-login cases now run on MTEST too (170 both, 284 EPP, 36 RRI, 25 skipped).
  Unit tests 2010 passed; `lint-imports` 15 kept; `pytest -n 8 tests/integration` on epp-docker 454 passed,
  63 skipped. MTEST integration: 205 passed, 311 skipped, 1 failed (`domain_update/test35`, a later command
  refused with `56000000013` after the create); it passed when run again.

- T22 (maintainer, 2026-11-14): `domainName.processes.create.active_at_once` became `success_status`, a list; a
  case writes `"label": "{env:domainName.processes.create.success_status}"` and the response holds one of its entries
  (`OneOf`). EPP: `ok`. MTEST, observed: `pendingCreate` right after the create, `ok` a step later, by timing; and
  `inactive` (documented `failed`). The 19 changed cases: epp-docker 19 passed; MTEST 7 passed, 12 skipped.

- T23 (maintainer, 2026-11-14): no case ran into `inactive`: the 19 cases give an `a` record, which passes the
  check (seen: `pendingCreate`, `ok`); the `ns` cases on MTEST (limits_domain 26, 27, 37, 38, 53, 54, 57) assert no
  status. `inactive` left `success_status`; new fact `failed_dns_status` (MTEST `[inactive]`, EPP null) and
  `domain_create/test43` (RRI only), passed on MTEST; the 19 cases passed again on both.

## Open questions

- None.
