# Plan: RRI release of a domain name, TRANSIT as releaseProcess (#252)

Branch `feature/252-rri-release-process`, stacked on `feature/251-rri-verification` (PR #259) -> #257 -> #256 -> #255 -> #253.
Merge order #253, #255, #256, #257, #259, this. The spec is committed (a0be5bd): docs/rri/rri-extension.md,
.spec/rri-extension.schema.json, .spec/spec-issues.md. It is the contract.

## Tasks

- [~] Plan approved by the orchestrator
- [ ] copy_models.sh: schema into src (the 3 doc tests turn green)
- [ ] Core: model, port, flow (`RriGateways.releases`)
- [ ] RRI part: TRANSIT command (`disconnect`), gateway, refusal codes
- [ ] RPP part: handler (create), mapping, DTO, OpenAPI fragment (create only), process registration, profile leaves
- [ ] Unit tests (mapping, wire, refusals, 501s, presets without the extension)
- [ ] MTEST: Holder needed?, `failed` refusal code, `domainTransit` queued for the releasing RegAcc; integration cases
- [ ] Docs: rri-extension.md (TBC replaced by findings), rri-5.0-reference.md §9/§14, gap-analysis.md, architecture.project.md
- [ ] Checks (lint-imports, unit, smoke incl. MTEST), draft PR

## Approach

One more Process Object of the Domain Name in the registered extension `de.denic.rpp.rri`, as authInfoIssueProcess is (create
only, 200 without Location). No RRI name in generic code.

Core (`extensions/rri/core`):
- `ports/release_gateway.py` (`create(name, keep_nameservers: bool, client_transaction_id)`), `RriGateways.releases`.
- `flows/release_flows.py`: `create_release(backend, name, keep_nameservers: bool | None, ctid)` -> the gateway with the applied
  value (`None` -> `True`), result carries the applied `keep_nameservers`. `model/release.py`: `Release(keep_nameservers: bool)`.

RRI part (`registry_adapter/rri/extensions/rri`):
- `commands/release/create.py`: domain TRANSIT, `disconnect` always sent (`"false"` when keep, `"true"` otherwise); the generated
  `Transit` binding exists in `domain_5_0`. Refusal codes through `run(codes=...)`: 63300022003 -> 403 02201 and 53000080009 -> 409
  02304 are in the general table already; the `failed` code is mapped explicitly once found (task above).
- `rri_release_gateway.py`, factory wiring.

RPP part (`extensions/rri/rpp`):
- `handlers/release_process_handlers.py` (create), `mapping/release_process.py` (request check with schema `releaseProcess.create`,
  `model_to_rpp` with `releaseProcess.read`), `dto/rpp_release_process.py` (`keepNameservers`).
- `schema/openapi_fragment.py`: `PROCESSES` gets `("releaseProcess", "domainNameReleaseProcesses", ...)`. As for
  authInfoIssueProcess, read/update/delete/list/read-by-id have no handler and answer 501 02101.
- `register_rri.py`: `PROCESSES["domainName"]` += `releaseProcess` (the #250 mechanism then maps the segment `releaseProcesses`
  to the extension: 400 02001 under a preset without it, left out of that preset's OpenAPI); profile leaf
  `domainName.processes.releaseProcess.operations` = `["create"]`.
- Schema file: `.spec/rri-extension.schema.json` copied to `src/.../rri-extension.schema.json` by `copy_models.sh`.

## Wire contract (from the spec, nothing new)

| Request | RRI | Answer |
|---|---|---|
| POST /domainNames/{name}/processes/releaseProcesses `{"@type":"releaseProcess"}` or `keepNameservers: true` | TRANSIT `disconnect="false"` | 200, no Location, `releaseProcess` with `keepNameservers: true` |
| same with `keepNameservers: false` | TRANSIT `disconnect="true"` | 200, `keepNameservers: false` |
| domain of another RegAcc (63300022003) | | 403 02201 |
| Registry Lock (53000080009), `failed` domain (code TBD) | | 409 02304 |
| `keepNameservers` not a Boolean | | 400 (schema) |
| Read, Update, Delete, list, read by id | none | 501 02101 |

## Decisions and findings

- (orchestrator, settled before the plan) see the task message: always send `disconnect`; refusals as above; MTEST checks only on
  objects the run's own setup creates, neutral prefixes; a released domain leaves the RegAcc, so teardown must not fail on it.

## Open questions, with recommendation

1. **Teardown of a released domain.** A released domain cannot be deleted by the RegAcc, nor taken back by registrar b (TRANSIT
   deleted AuthInfo1, AuthInfo2 only arrives by post). Teardown failures are warnings, never failures. Recommendation: the
   teardown has no delete for the domain, and says in its comment that MTEST keeps it (it keeps what cases create today); the
   contact holder is not deletable while the domain exists, so contacts are left too, with neutral prefixes. Confirm no
   run-level cleanup is wanted.
2. **Holder needed (63360082531).** Probed by the case itself: release a domain created with a holder. If MTEST demands a Holder
   on TRANSIT, the implementation takes the holder from a domain INFO before the TRANSIT (an extra command) and the appendix says
   so. If it does not, the TBC aside becomes a finding and no INFO is sent.
3. **`failed` domain.** Produced only if a create with a predelegation failure is possible from the run's own setup (e.g. name
   servers the registry's check rejects, if that is not refused at create). If it cannot be produced safely, the code stays unknown,
   the refusal is mapped by class and the spec/appendix says so (a spec-issue note for the orchestrator).
4. **`domainTransit` queued for the releasing RegAcc.** Checked by reading the queue of `a` after the release case (queue is
   drained by the run setup/teardown; the case `exclusive: ["message_queue"]`). Recorded in rri-5.0-reference §9/§14 and the appendix.

## Orchestrator decisions (plan approved)

1. Teardown: no delete step, with a comment. Cases that actually release a domain are not smoke (full run only); cheap cases
   (foreign 403, read 501) that release nothing stay smoke. State it in the case comments and in testing.project.md if it lists
   such cases.
2. Holder: probe as described.
3. `failed` domain: try from the run's own setup; if it cannot be produced, keep the class mapping, say so in the appendix, and
   file an issue like #258 (refusal code unknown, class 5 would answer 500 instead of 409); report its number.
4. domainTransit queue check: as described.

## Findings (MTEST, 2026-11-28, own setup objects only)

- TRANSIT without a Holder succeeds (domain with a holder contact); 63360082531 did not arise. No INFO is sent.
- TRANSIT of a `failed` domain (created with name servers that do not serve it, status `inactive` on RPP): 53000080012 "Domain
  "Status" is "failed"", class 5 -> 500 before the mapping; now 409 02304 for the release only. No issue to file.
- `disconnect="true"`: the domain's DNS data became one A entry at `www.<name>.`; `false` kept the `@` record. The released
  domain reads for registrar a with `regAcc` DENIC-1000004 ("DENIC eG - TRANSIT").
- Queue of the releasing RegAcc empty right after TRANSIT: no `domainTransit` for the own TRANSIT (not asserted by a case).
- Validation error of a non-Boolean `keepNameservers` is 400 02001 (not 02005).
- Cases `release_process/test1`, `test2` release a domain (not smoke, full run only); `test3` to `test6` smoke.
- Checks of 295176b: lint-imports 32 kept; unit 3397 passed; smoke 251 passed 581 skipped (incl. MTEST); release_process on MTEST 6 passed (test1 and test2 release domains).

## Review round 1 (4 low findings, all fixed)

1. testing.project.md: release_process/ its own item; exception for test1/test2 in the "delete their domains" sentence.
2. gap-analysis.md §1 summary now follows the Fit column of §2: 8 + 12 + 1 + 0 = 21.
3. test1 asserts spClientId DENIC-1000004 of the released domain; the queue claim is marked "seen once, not checked by a case"; the `failed` refusal is checked by test5.
4. Appendix bullet on disconnect="true": one A entry at www.<name>. on MTEST (checked by test2).
- Checks of 65fd77c (review round 1): lint-imports 32 kept; unit 3397 passed; smoke 251 passed 581 skipped; release_process on MTEST 6 passed.
