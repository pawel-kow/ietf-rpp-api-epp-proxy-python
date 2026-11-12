# Plan: review of field coverage and probes of backend limits (#136)

Branch `feature/136-limit-probes` from `main` at 414a86e.

## Tasks

- [x] T1 Review of the integration suite per data object field: `docs/testing/integration-test-review.md`
- [x] T2 Limits of the EPP test server and RRI MTEST: `docs/testing/backend-limits.yaml`
- [x] T3 Correction (maintainer): FQDN lengths are defined by DNS (RFC 1035 §2.3.4), not a gap
- [x] T4 Runner: `{pad:N:TEXT}` for a name or id of an exact length (unit tests first)
- [~] T5 Probe cases `limits_domain/`, `limits_contact/`, `limits_host/`, with environment facts for the limits
      that differ by server
- [ ] T6 Run on epp-docker (needs `.env`), record the outcomes, file the confirmed defects, mark them `skip`
- [ ] T7 Open boundaries of the drafts into `.spec/spec-issues.md`
- [ ] T8 Docs: `testing.project.md` (placeholder, facts, the new groups), the review updated with the outcomes
- [ ] T9 Checks: `lint-imports`, `pytest -n 8`; MTEST run `RPP_TEST_ENV=rri-mtest pytest -n 4 tests/integration`
      (pending: needs a machine on the allowlist)
- [ ] T10 Draft PR

## Findings (evidence)

1. No case tests a value at or over a limit; no array is filled to its maximum (review §2).
2. EPP test server (container `epptest-epp-server-1`, read-only): MariaDB `sql_mode` has no `STRICT_*`, so values
   over a column are cut; `domain.name` is varchar(68); nameservers, contacts per role and host addresses are counted
   per command, not per object (`command-update.cgi`); `secdns.digest` varchar(64) leaves out digest type 4.
3. RRI XSD failures (`83000000004`) and class-5 codes map to 500 `02400` in `registry_adapter/rri/result_codes.py`.
4. The proxy answers more registrants than `profile.max_registrants` with 501 (`rpp/mapping/domain/domains.py:43`).
5. `tests/integration/test_domain_create.py` and `test_domain_delete.py` collect no test.

## Decisions

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
  records (another limit is hit first), a request over 64 KiB, a dot in a contact id, a city with a digit.

## Results

## Open questions

- `.env` with the epp-docker credentials is missing in this container, so T6 waits for it.
