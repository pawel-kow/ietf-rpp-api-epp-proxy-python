# Plan: RRI authorisation information processes (#250, relates to #134)

Branch `feature/250-rri-authinfo-processes`, stacked on `feature/249-rri-organisations` (PR #256) -> #255 -> #253. Merge
order #253, #255, #256, this. The spec is committed (b2cf658): docs/rri/rri-extension.md, .spec/rri-extension.schema.json,
.spec/spec-issues.md. It is the contract.

## Tasks

- [x] Plan approved by the orchestrator
- [x] copy_models.sh: schema into src
- [x] Core of the extension: models, ports (`RriGateways`), flows
- [x] RRI part: commands (create with `expire`, info of AuthInfo1, delete, CREATE-AUTHINFO2), gateways, refusal codes
- [x] Handlers, OpenAPI fragment, preset check of the process paths, profile leaves
- [x] Unit tests (mappings, refusals, wire, preset signalling)
- [x] MTEST: probe the expiry limit (#134) and the AuthInfo2 status refusal; integration cases
- [x] Docs: gap-analysis.md, architecture.project.md, testing.project.md if cases need it, rri-extension.md facts found
- [~] Checks (lint-imports, unit, smoke incl. MTEST), draft PR

## Approach

Two Process Objects of the Domain Name added by the registered extension `de.denic.rpp.rri`, no RRI name in generic code.

Core (`extensions/rri/core`):
- `model/auth_info_process.py` (`AuthInfoProcess`: `expiry_date: date | None`, `sponsor_id`), `model/auth_info_setting.py`
  (`AuthInfoSetting`: `name`, `password`, `expiry_date | None`).
- `ports/auth_info_process_gateway.py` (`create(setting)`, `info(name)`, `delete(name)`), `ports/auth_info_issue_gateway.py`
  (`create(name)`); `RriGateways` gets `auth_info_processes` and `auth_info_issues`.
- `flows/auth_info_process_flows.py`: create (gateway create, then `info` read-back; read-back failure does not fail the
  create), read (info; no AuthInfo1 -> `OBJECT_DOES_NOT_EXIST`; `require_sponsor` for a foreign domain: INFO shows others only
  `authInfo: true`), delete. `flows/auth_info_issue_flows.py`: create.

RRI part (`registry_adapter/rri/extensions/rri`):
- `commands/auth_info_process/{create,info,delete}.py`, `commands/auth_info_issue/create.py`; create reuses the shared
  `rri_create_auth_info1` of the domain commands, extended with `expire` (`YYYYMMDD`); `rri_delete_auth_info1` reused.
- info: domain INFO, the date is the calendar date of `domain:authInfo1` as the registry writes it (not converted to UTC; the
  domain's `carried_over` holds the UTC form and stays as is), sponsor from `regAcc`.
- Command-specific refusal codes through `run(codes=...)`: 63391068618 and 63391068603 -> `PARAMETER_VALUE_RANGE_ERROR` (400
  02004). 63391068704, 63393068704, 63392068709 are in the general table already (409 02302, 409 02302, 404 02303).
- CREATE-AUTHINFO2: status refusal by class mapping until MTEST shows the code (task above).

RPP part (`extensions/rri/rpp`):
- `handlers/auth_info_process_handlers.py` (create, read, delete) and `handlers/auth_info_issue_process_handlers.py` (create),
  thin presenters over the flows. Create answers 200, no Location. `mapping/auth_info_process.py` (rpp_to_model: method
  `authinfo` only else 501 02102, RRI charset/length else 422 02306 as the domain `authInfo` does today; model_to_rpp),
  `mapping/auth_info_issue_process.py`.
- `schema/openapi_fragment.py`: the paths of the transfer process family of the domain (without approve/reject) renamed to
  `authInfoProcesses` and `authInfoIssueProcesses`, as the request contact paths are made from the contact's. Operations with
  no handler (list, read by id, update, read/delete of the issue process) answer 501 02101 as every operation without a handler.

## Wire contract (from the spec, nothing new)

| Request | RRI | Answer |
|---|---|---|
| POST /domainNames/{name}/processes/authInfoProcesses | CREATE-AUTHINFO1 (hash, `expire`), INFO | 200, no Location, `authInfoProcess` with the expiry date that applies |
| GET .../authInfoProcesses/latest | INFO `authInfo1` | 200 expiry date; none 404 02303; not sponsor 403 02201 |
| DELETE .../authInfoProcesses/latest | DELETE-AUTHINFO1 | 200; 63392068709 404 02303 |
| POST .../authInfoIssueProcesses | CREATE-AUTHINFO2 | 200, no Location, `{"@type":"authInfoIssueProcess"}` |
| second create 63391068704 / 63393068704 | | 409 02302 |
| expiry refused 63391068618 / 63391068603 | | 400 02004 |
| method not `authinfo` | | 501 02102 |

The secret (`authdata`) is never returned and never logged.

## Decisions and findings

- (orchestrator, settled before the plan) see the task message: no proxy-side limit on the expiry date, domain `authInfo`
  member unchanged, AuthInfo2 status refusal by class mapping until found on MTEST, then 409 02304.
- MTEST reachable from this machine: `domain_availability::test3-a_label` passed (7 s) before starting.
- The drafts' OpenAPI has no `domainNames_processes` handler: a read of the Processes Object is 501 today, so the new
  `rpp:extends` members of `processes.read` are schema only.

## Open questions, with recommendation

1. **Preset check of the process paths.** `PresetMiddleware` checks only the first path segment (`requestContacts`) against the
   extension of the preset. The new paths start with `domainNames`, so under a preset without the extension the body definition
   `authInfoProcess.create` is unknown (no 400 02001 as the `/requestContacts` paths give). Recommendation: a `processes` tuple on
   `RegisteredExtension` (identifiers `authInfoProcess`, `authInfoIssueProcess`) handed to `RppExtension` by `register_all`; the
   middleware also maps the segment after `/domainNames/{name}/processes/` (plural of the identifier, core §16.1) to its
   extension and answers the same 400, and `outside_the_preset` leaves those operations out of the preset's OpenAPI document
   as it does the objects. No change to the schema file or the spec.
2. **Profile leaves.** `profile_layer`/`profile_leaves` of the extension: `domainName.processes.authInfoProcess.operations`
   (`create`, `read`, `delete`) and `domainName.processes.authInfoIssueProcess.operations` (`create`), tuples like
   `transfer.operations`, read by the test selectors only (no enforcement: a backend without the extension has no paths).
   Confirm or drop.
3. **Read-back fails after a create.** The create succeeded, so answer 200 with the requested date if one was sent, else
   `{"@type":"authInfoProcess"}` (spec: "when the server knows it"), and log the failure by code. Alternative 202; not
   recommended, the action is complete.
4. **Hash in the log.** The shared `rri_create_auth_info1` is sent loggable today, and the SHA-256 of an 8 to 16 character
   secret can be brute forced. Recommendation: send CREATE-AUTHINFO1 with `loggable=False` in the shared function (it covers the
   domain create/PUT/PATCH too; a security fix, no wire change). Confirm.
5. **Sponsor check of DELETE.** Left to the registry (63300022003 -> 403 02201), as for the other deletes; READ checks `clID`
   because INFO of a foreign domain succeeds. Confirm.
6. **MTEST date probe** creates AuthInfo1 on a domain made by the run (own domain, own teardown), tries `expire` of today+1,
   +2, +7, +14, +29, +30, and records the accepted maximum in #134 (close it if the PR settles it). The AuthInfo2 refusal probe
   is time-boxed: a domain state the registry refuses, if one can be made without touching other runs' domains; else class
   mapping stays and the spec-issue/doc says so.

## Decisions of the orchestrator (plan approved)

1. `processes` on `RegisteredExtension` and `RppExtension` (via `register_all`); `PresetMiddleware` maps the segment after
   `.../processes/` to its extension and answers as for an extension's object path under a preset without it;
   `outside_the_preset` drops those operations. Generic and tested, also that base processes are unaffected.
2. The two profile leaves, read by the test selectors.
3. Read-back failure after create: 200 with the requested date if sent, else `{"@type":"authInfoProcess"}`, logged by code only;
   one sentence in the appendix if not covered (text in the Draft PR report).
4. `loggable=False` for the shared CREATE-AUTHINFO1 and anything else carrying a hash or secret (check DELETE, CHPROV, INFO with
   AuthInfo); test that the hash is not logged.
5. DELETE left to the registry (63300022003 -> 403 02201); READ checks the sponsor (foreign domain 403 02201).
6. Both MTEST probes, AuthInfo2 refusal time-boxed; findings in docs/rri (reference open points / gap analysis) and #134.

## Findings (MTEST, 2026-11-28 07:58 Europe/Berlin)

- CREATE-AUTHINFO1 `expire` of today+0, +2 .. +30 days: 63391068618; only today+1 accepted (the default, no `expire`, is the same
  end of the next day). One probe case per value and a single case with all values both agree. Recorded in #134, the reference (open
  point 6) and the extension appendix.
- `domain:authInfo1` is the instant of expiry: `expire=20261129` reads back `2026-11-30T00:00:00+01:00`. The spec said the Expiry
  Date is the date of `authInfo1`, which would answer a day after the request: the implementation answers the last valid day (the
  instant less a microsecond, in the registry's offset). **Spec appendix reworded; needs the maintainer's confirmation.**
- The CREATE-AUTHINFO1 reply holds `createAuthInfo1Data/expire` (the instant). Not used: the INFO read-back is the specified way.
- CREATE-AUTHINFO2 works on a `pendingCreate` domain. No domain state that refuses it could be made (time-box): the code stays
  unknown, the class mapping stays (6 -> 422 02306), not 409 02304.
- Added `{date:+Nd}` to the integration placeholders (documented in testing.project.md).
- Hash of CREATE-AUTHINFO1 is no longer printed (CHPROV was already not).

## Review round 1 (three low findings, all fixed)

1. info.py: the full value (offset, fraction, `24:00:00`), an unreadable value (xsdata leaves the text) is an AuthInfo1 without a date, logged by field name; model `exists`.
2. process owners keyed by (collection, segment); `processes` names the owning object.
3. test: base document leaves the process paths out, rri keeps them.

## Check results (commit b41a37c, no edits during the runs)

- `PYTHONPATH=src lint-imports`: 32 kept, 0 broken.
- `pytest -n 4 tests/unit`: 3259 passed.
- `pytest -n 4 -m smoke tests/integration`: 241 passed, 511 skipped (8 min), MTEST included (the reachability case passed first;
  `authinfo_process/test1` is a smoke case). The whole group `authinfo_process/` (9 cases) passed on MTEST on its own too.
