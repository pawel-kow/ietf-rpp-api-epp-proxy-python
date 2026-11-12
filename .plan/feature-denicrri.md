# Plan: DENIC RRI 5.0 as a second registry backend (#126)

Branch `feature/denicrri`, one draft PR for all phases of [docs/rri/refactoring.md](../docs/rri/refactoring.md) §6.
The maintainer asked to work through the phases without waiting for confirmation, pushing progress to the draft PR.

## Tasks

- [x] Mutex, merge `origin/main` (#120 phases 2–6 are merged) into the branch.
- [x] Extract the EPP test values for `.env` (`TEST_EPP_*`), probe MTEST.
- [x] R1: test environments, `.env`, placeholders, selectors, cases moved; the new profile facts.
- [x] R2: `TCPClient` framing; the models widened (§3.6), EPP mapping unchanged.
- [x] R3: `rri/session`, `rri/xml` (generated), CTIDs, result codes, `FakeRriClient`, `RriSettings`, `RRI_PROFILE`,
      composition, `rri-mtest.yaml`; LOGIN/LOGOUT on MTEST. `SerialSession` in `common/session` shared by both clients.
- [x] R4: RRI domains (CHECK, INFO, CREATE + AuthInfo1, UPDATE/CHHOLDER, DELETE, RESTORE), `derived_update.update`.
- [x] R5: RRI contacts (CHECK, INFO, CREATE, UPDATE with verification carried over).
- [x] R6: RRI messages (QUEUE-READ, QUEUE-DELETE). Every message is a service notice (see open points).
- [x] R7: transfer per Q3 option C (501 `02101` from the profile), Q8–Q10 and Q16 not exposed.
- [x] R8: docs (architecture, testing, security, process, overview, README, refactoring.md status).
- [x] Full EPP run and MTEST run on the final state, recorded below.
- [x] Follow-ups filed: #131 (REQUEST contacts), #132 (typed queue messages), #133 (CHPROV and the rest not exposed),
      #134 (AuthInfo1 lifetime), #135 (plan files left on main).
- [~] Maintainer review; then `git rm` this plan, release the mutex.

## Decisions

- **One branch and one draft PR** instead of one per phase, as the maintainer asked. Each phase is its own series of
  commits.
- **Open questions of gap-analysis §7 take the proposal** written there, as the maintainer asked to proceed without
  confirmation: Q1 first holder is `registrant`, the others `contacts` labelled `registrant`; Q2 labels
  `generalRequest` and `abuse`; Q3 option C (transfer answers 501 `02101`); Q4 30 days, charset checked up front
  (422 `02306`); Q5 `failed` → `inactive`, DISPUTE left out; Q6 RESTORE without a report, a report → 501; Q7 see
  below; Q8–Q10 not exposed; Q11 refuse `lgr` unless one is configured;
  Q12 yes; Q13 DENIC refuses; Q14 synthesise `ok`; Q15 as proposed; Q16 out of scope; Q18 `<cltrid>-n`; Q19 409.
- **EPP credentials in `.env` too** (maintainer): the EPP environment names `TEST_EPP_REGACC1`/`_PASSWORD` and
  `TEST_EPP_REGACC2`/`_PASSWORD` instead of writing `foo`/`bar` and `baz`/`qux` into its descriptor. The wrong
  password and unknown user forms are not secrets and stay in the descriptor.
- **Handle prefixes in `.env`** (maintainer): `TEST_<ENV>_REGACCn_PREFIX`, because a handle must carry the prefix
  configured for its account, and the EPP and RRI accounts differ (`FO-`/`BA-` on EPP, `DENIC-<n>-<suffix>-` on RRI).
  The descriptors name the variable instead of a fixed prefix.
- **CTID** (gap Q18): the client's `RPP-Cltrid` is the CTID of the first write of a request when it is a token of 3
  to 60 characters, `<cltrid>-n` of the n-th; otherwise a new UUID. Every answer echoes the client's id.
- **Q7 as proposed** (maintainer, after review): a request whose second command fails answers 202 with the first
  command's headers and a logged warning. `PartiallyApplied` in `core/result` carries it, and `read_back` does not
  read it back.
- **Reading a REQUEST contact** answers 501 `02102`: RPP has no Card form for a URI template yet (gap Q2), follow-up.
- **A domain in its redemption period reads with what RRI shows** (maintainer): its INFO names no sponsor, which RPP
  requires, so `spClientId` is the placeholder `unknown` (spec-issues.md, "Sponsor of a deleted domain").
- **Every case runs on both backends** unless it needs a function one lacks (maintainer). The contacts get a phone
  and a full address, the domains an `a` record and a registrant, passwords RRI's characters; differences are
  selected by profile and environment facts. RRI counterparts: `domain_update/test35` to `test37`.
- **Pass-through** (maintainer): the RRI adapter refuses only what an RRI request has no place for (a person's name
  on an ORG, 501 as accepted; a contact authInfo; a `uName` that is not the name; an AuthInfo1 RRI does not take,
  as it receives only the hash). Name changes, clearing a required contact member and a domain without DNS data go
  to RRI, which refuses them (422 `02306`; `83000000004` for the missing DNS data, the XSDs). An `lgr` is not sent.
- **Contact kind** (maintainer): an `org` card is an RRI ORG, an `individual` with an organisation a PERSON with
  `organisation` (`contact_kind_held`; EPP still refuses it). An update keeps the type RRI holds, a PATCH the kind.
  Cases: `draft_contact/test2`, `contact_update/test24`, `test35`.
- **New profile facts** beyond refactoring.md §3.7: `contact_auth_info` (EPP requires a contact authInfo, RRI has
  none; the contact mapper refuses one), `contact_kind_held`, `domain_dns_required`, `contact_phone_required` and
  `contact_name_changeable` (the last three left to the registry, read by the test selectors).
- **A poll on RRI answers 1301/1300** like EPP, so a client sees the same codes.
- **The EPP cases** that create domains without DNS data or contacts without a phone skip on RRI by those facts at
  group level. The cases that run on both backends are the new `domain_lifecycle/` group, plus the availability,
  discovery and message groups.

## Findings

- MTEST is reachable from this devcontainer (egress `81.91.160.182` is allowlisted): LOGIN and LOGOUT succeed for
  both RegAccs over XML 5.0, with the `13000000011` info on every reply.
- On MTEST, each RegAcc uses the same `REQUEST` contact for the General Request and the Abuse role
  (`TEST_RRI_REGACCn_GEN_REQ` equals `TEST_RRI_REGACCn_ABUSE`).
- MTEST queue messages include `msg:contactDelete`, which ref §9 does not list.
- MTEST probe: a domain CREATE with an `A` and an `MX` record and no NS succeeds with `pendingCreate`
  (`53000080014`); an MX exchange must resolve (`63300083005` otherwise). CREATE-AUTHINFO1 without `expire` answered
  an expiry two days ahead, not 30, and `expire` = today + 30 days is refused (`63391068618`, #134). INFO after DELETE shows `redemptionPeriod`. Handles come back in upper case.
- `.plan/refactor-116-backend-port.md` and `.plan/refactor-117-backend-profile.md` are on `main` although their PRs
  are merged (left over, not removed by #118/#121).

## Test runs

| When | Command | Result |
|---|---|---|
| Before (`0c4f6ac` + main) | `PYTHONPATH=src lint-imports`; `pytest -n 8` | 12 contracts kept; 2149 passed, 5 skipped |
| R1 + R2 (`bf7f223`) | the same | 12 contracts kept; 2209 passed, 6 skipped (the same integration skips: #49, #50, #54) |
| R3–R8 (`1bc9732`) | `PYTHONPATH=src lint-imports`; `pytest -n 8` (EPP) | 15 contracts kept; 2272 passed, 8 skipped (#49, #50, #54, the two empty legacy modules, three RRI-only `domain_lifecycle` cases) |
| R3–R8 (`1bc9732`) | `RPP_TEST_ENV=rri-mtest pytest -n 4 tests/integration` (MTEST) | **20 passed**, 290 skipped (each skip names its fact); `domain_lifecycle` 7 of 7 |
| Review round 1 | `PYTHONPATH=src lint-imports`; `pytest -n 8` (EPP) | 15 contracts kept; 2287 passed, 9 skipped |
| Review round 1 | MTEST, `pytest -n 4 tests/integration` | **105 passed**, 208 skipped (each skip names the function RRI lacks); the one failure of the full run, `domain_lifecycle/test1` (a deleted domain now reads), fixed and rerun |
| Review round 2 (pass-through) | `PYTHONPATH=src lint-imports`; `pytest -n 8` (EPP) | 15 contracts kept; 2290 passed, 10 skipped |
| Review round 2 (pass-through) | MTEST, `pytest -n 4 tests/integration` | **108 passed**, 206 skipped |

## Open questions

None blocking.
