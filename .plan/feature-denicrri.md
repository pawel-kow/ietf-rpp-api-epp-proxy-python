# Plan: DENIC RRI 5.0 as a second registry backend (#126)

Branch `feature/denicrri`, one draft PR for all phases of [docs/rri/refactoring.md](../docs/rri/refactoring.md) §6.
The maintainer asked to work through the phases without waiting for confirmation, pushing progress to the draft PR.

## Tasks

- [x] Mutex, merge `origin/main` (#120 phases 2–6 are merged) into the branch.
- [x] Extract the EPP test values for `.env` (`TEST_EPP_*`), probe MTEST.
- [~] R1: test environments, `.env`, placeholders, selectors, cases moved; the new profile facts.
- [ ] R2: `TCPClient` framing; the models widened (§3.6), EPP mapping unchanged.
- [ ] R3: `rri/session`, `rri/xml` (generated), CTIDs, result codes, `FakeRriClient`, `RriSettings`, `RRI_PROFILE`,
      composition, `rri-mtest.yaml`; LOGIN/LOGOUT on MTEST.
- [ ] R4: RRI domains (CHECK, INFO, CREATE + AuthInfo1, UPDATE/CHHOLDER, DELETE, RESTORE), `derived_update.update`.
- [ ] R5: RRI contacts (CHECK, INFO, CREATE, UPDATE with verification carried over).
- [ ] R6: RRI messages (QUEUE-READ, QUEUE-DELETE, type mapping).
- [ ] R7: transfer per Q3 (option C: 501), Q8–Q10, Q16 not exposed.
- [ ] R8: docs.
- [ ] Before merge: file unfixed defects as issues, `git rm` this plan, release the mutex.

## Decisions

- **One branch and one draft PR** instead of one per phase, as the maintainer asked. Each phase is its own series of
  commits.
- **Open questions of gap-analysis §7 take the proposal** written there, as the maintainer asked to proceed without
  confirmation: Q1 first holder is `registrant`, the others `contacts` labelled `registrant`; Q2 labels
  `generalRequest` and `abuse`; Q3 option C (transfer answers 501 `02101`); Q4 30 days, charset checked up front
  (422 `02306`); Q5 `failed` → `inactive`, DISPUTE left out; Q6 RESTORE without a report, a report → 501; Q7 202 with
  the first command's headers and a logged warning; Q8–Q10 not exposed; Q11 refuse `lgr` unless one is configured;
  Q12 yes; Q13 DENIC refuses; Q14 synthesise `ok`; Q15 as proposed; Q16 out of scope; Q18 `<cltrid>-n`; Q19 409.
- **EPP credentials in `.env` too** (maintainer): the EPP environment names `TEST_EPP_REGACC1`/`_PASSWORD` and
  `TEST_EPP_REGACC2`/`_PASSWORD` instead of writing `foo`/`bar` and `baz`/`qux` into its descriptor. The wrong
  password and unknown user forms are not secrets and stay in the descriptor.

## Findings

- MTEST is reachable from this devcontainer (egress `81.91.160.182` is allowlisted): LOGIN and LOGOUT succeed for
  both RegAccs over XML 5.0, with the `13000000011` info on every reply.
- On MTEST, each RegAcc uses the same `REQUEST` contact for the General Request and the Abuse role
  (`TEST_RRI_REGACCn_GEN_REQ` equals `TEST_RRI_REGACCn_ABUSE`).
- MTEST queue messages include `msg:contactDelete`, which ref §9 does not list.
- `.plan/refactor-116-backend-port.md` and `.plan/refactor-117-backend-profile.md` are on `main` although their PRs
  are merged (left over, not removed by #118/#121).

## Test runs

| When | Command | Result |
|---|---|---|

## Open questions

None blocking.
