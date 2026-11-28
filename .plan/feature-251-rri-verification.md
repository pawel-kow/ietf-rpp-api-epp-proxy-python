# Plan: RRI contact verification information and the verification process (#251)

Branch `feature/251-rri-verification`, stacked on `feature/250-rri-authinfo-processes` (PR #257) -> #256 -> #255 -> #253. Merge
order #253, #255, #256, #257, this. The spec is committed (90f806d): docs/rri/rri-extension.md, .spec/rri-extension.schema.json,
.spec/spec-issues.md. It is the contract. Mutex `.agent-sync.yml` taken for this branch.

## Tasks

- [x] Read the spec, #250's plan and code, PR #247's entry "Full update of a member an extension adds"
- [x] Plan approved by the orchestrator
- [x] copy_models.sh: schema into src
- [x] Generic: `CONTACT_MEMBERS` (`MemberMappers` for the contact), `Contact.extensions` / `ContactReplacement.extensions`, mapper functions take `extensions`, `MemberMappers.split(stated=)`
- [x] Core of the extension: models (verification information, contact verifications, holder verification, verification process), port, flow
- [x] RRI part: contact members hook (`RriExtensionPart.contact_members`), XML of the blocks, gateway wiring, refusal codes, verification process INFO
- [x] Handlers, OpenAPI fragment, preset check, profile leaves
- [x] Unit tests (mappers, wire, flows, XML, refusals, presets)
- [x] MTEST integration cases
- [x] Docs: gap-analysis.md (§3.2, §4.5, Q16 left), architecture.project.md, testing.project.md, rri-5.0-reference.md facts
- [x] Checks, draft PR

## Approach

### Generic (no RRI names)

The contact gets the mechanism the domain and the organisation have (#183, #249).
- `rpp/mapping/contact/contact_members.py`: `CONTACT_MEMBERS = MemberMappers(merge=<union of dicts>)`. The model holds what an extension
  adds to a contact as `extensions: dict[str, object]`, a typed object per extension id (as `Organisation.extensions`), on `Contact`
  (create, read) and on `ContactReplacement` (full update, patch). A mapper's `to_model(present)` returns `{extension_id: object}`,
  `to_rpp(contact)` reads `contact.extensions[extension_id]`. #183's note that the first non-role member generalises `DOMAIN_MEMBERS`'
  `to_model` is not needed: the contact is another registry with its own `merge`, and the domain's stays as it is.
- `MemberMappers.split(rpp, schema, extensions, stated=None)`: with `stated` (the member names the request restates) a mapper that
  declares one of them is converted even when its member is absent from `rpp` (`to_model({})`), and a mapper with none is dropped
  unconverted. Without it, as today (create, domain). A full update states every member of `contact.update`: an omitted member
  under a preset that has the extension is therefore the empty value (the removal), and under a preset without it the
  mapper is not asked and the replacement has no entry (the backend keeps what it holds): PR #247's rule. A patch states the members
  its operations name (path `/<member>`), so a patch that leaves `verifications` alone never converts the stored blocks.
- `rpp/mapping/contact/*`: `contacts.rpp_to_model/model_to_rpp`, `contact_replacement`, `contact_patch` take `extensions` (handlers pass
  `request_profile().extensions` / `response_profile().extensions`, as the domain's do). The members are `changeable` in a full
  update and in a patch (`/<member>` takes the read path: `NeedsCurrentState`, spec: "PATCH on the read path"). A patched member is validated
  against the `contact.update` definition (enumerations, `uniqueItems`) before it is converted, because the read definition does not enforce them.
- Adapter: `RriExtensionPart.contact_members` (a small object with `read(contact InfoData) -> object|None` and `fields(object) -> dict`, the
  keyword fields of contact CREATE/UPDATE), loaded by name from the extension's RRI module like `ORGANISATION_MEMBERS`. `RriContactGateway`
  fills `Contact.extensions` on INFO from the parts, and on create/update asks the part for the fields of the entry of the wanted
  `extensions`; with no entry it keeps today's behaviour (`carried_over`, the raw blocks of the INFO it read), so `base` and the partial update through `contact_application.apply`
  keep the blocks, and a backend without the extension's part loses nothing.

### rri extension (`de.denic.rpp.rri`)

Core: `model/verification_information.py` (`claims: list[str]`, `result`, `reference`, `date`, `evidence`, `method`, `trust_framework`;
the read side has optional ones), `model/contact_verifications.py` (`blocks: list[VerificationInformation]`), `model/holder_verification.py`
(`handle`, `verifications`), `model/verification_process.py` (`hold_deadline`, `deletion_deadline`, `holders`, `sponsor_id`;
`reduced()` for another client: no handles, claims and result only), `ports/verification_process_gateway.py` (`info(name, authorization)`),
`flows/verification_process_flows.py` (`read_verification_process`: foreign domain without authorisation 403 02201; no deadline 404 02303;
foreign with authorisation is reduced by the flow, whatever the gateway returned, as the spec says MUST NOT). `RriGateways.verification_processes`.

RPP part: `mapping/contact_members.py` (`ContactVerificationMembers`: `members = ("verifications",)`; `to_model` builds `ContactVerifications`, `to_rpp` the blocks, omitted when none),
`mapping/verification_process.py` (+ `dto/rpp_verification_process.py`, `rpp_holder_verification.py`, `rpp_verification_information.py`),
`handlers/verification_process_handlers.py` (`domainNameVerificationProcesses_read`; the rest of the paths have no handler: 501 02101), registered in `register_rri.py`
(`CONTACT_MEMBERS.add`, `PROCESSES["domainName"]` gets `verificationProcess`, profile layer leaf `domainName.processes.verificationProcess.operations = ["read"]`).
OpenAPI fragment: one more entry in `PROCESSES` (paths of the transfer processes, as #250).

RRI part: `contact_members.py` in `registry_adapter/rri/extensions/rri` (blocks `xsi:type verificationInformationType`, claims lower case, dates in UTC, all elements,
read from `VerificationInformation` objects of the INFO; the registry's value as it states it, an unreadable timestamp is left out and logged by field name),
`commands/verification_process/info.py` (domain INFO `recursive=true`, `authInfo` the value of `RPP-Authorization`, sent with `loggable=False`; deadlines
`verificationDeadlineBeforeDedelegation`/`BeforeDeletion` in UTC; holders from `domain:contact role="holder"` in order with their blocks; sponsor from `regAcc`),
`rri_verification_process_gateway.py`, factory. The comparison `same_contact` includes the blocks (canonical form: lower case claims, UTC date), so a PUT that changes only
the verifications is sent and one that changes nothing is not.

## Wire contract (from the spec, nothing new)

| Request | RRI | Answer |
|---|---|---|
| POST/PUT contact with `verifications` (0-5) | CREATE/UPDATE with blocks | 201/200, read back with the blocks (sponsor) |
| PUT contact without `verifications`, preset `rri` | UPDATE without blocks | blocks removed |
| PUT contact without `verifications`, preset `base` | UPDATE with the blocks of the INFO | blocks kept |
| PATCH contact | INFO, patch on the read, UPDATE | `/verifications` only when named |
| 63200041860/61/62/64/65/66 | | 400 02005 |
| 63200041863, 63200041867 | | 422 02306 |
| GET .../processes/verificationProcesses/latest, sponsor | INFO recursive, own | 200 full, no Location |
| same, other client with `RPP-Authorization` | INFO recursive + `authInfo` | 200 reduced (no `holder`, claims and result) |
| same, other client without it | INFO | 403 02201 |
| no deadline | | 404 02303 |
| create/update/delete of the process | | 501 02101 |

Verification elements and values are never logged by the proxy. `loggable=False` for the commands that carry them (see open question 5). A registry value the client cannot fix is left out and logged by field name, never a 500.

## Open questions, with recommendation

1. **Spec example of the patch.** The example "contact partial update request that adds the result of a failed verification" (rri-extension.md, Update) has
   `"path": "/verifications/-"`. RPP's JSON Patch has no `-` (json draft §5.2: `add` to the array path appends; `/verifications/-` is a 400 here: "does not point to a
   property"). Recommendation: change the example to `"path": "/verifications"` (one line in the approved spec) and use that body in the wire test.
2. **63450064002 (block on a REQUEST contact).** The spec's refusal table does not list it, and the proxy cannot send it: a block is built only for a `contact`, and a request contact (REQUEST) has no verifications. Recommendation: no
   entry (the class mapping, 422 02306, applies if it ever occurs); say so in the appendix? No: keep the table as approved.
3. **Domain INFO of a holder without handle.** Empty `holders` with a deadline (the registry states no holder) cannot be a valid `verificationProcess.read` (`holders` 1+). Recommendation: treat it as no process, 404 02303, log "no holders" without values.
4. **The reduced form is applied in the core flow too**, not only by what RRI returns. Recommendation: yes (defence in depth for the MUST NOT).
5. **Printing of replies.** `TCPClient` prints every received message (known debt #14), so contact INFO/domain INFO replies with verification data and personal data are printed today.
   Recommendation: send contact CREATE/UPDATE that carry blocks and the recursive domain INFO with `loggable=False`, and make `loggable=False` suppress the print of the reply as well
   (a small change in `serial_session`/`tcp_client`, covers CHPROV too). Contact INFO (the base read) stays as it is (debt #14). Confirm, or leave the reply print alone and note it in security.project.md.
6. **MTEST probes** (time-boxed, only domains/contacts of the run): create/update with a block, read back, PUT without `verifications` under `rri` (removed) and under `base` (kept), refused combination (63200041867), the verification process of a domain whose holder's pre-verification failed (immediate high risk level, reference §8), without a deadline,
   foreign reads with registrar b with and without `RPP-Authorization`. If MTEST gives no deadline, the process is covered by unit tests with XML only and the plan says so.

## Decisions

- (orchestrator, settled before the plan) see the task message.
- (orchestrator, plan approved) 1. patch example path becomes `/verifications` (one-line spec fix, no Changes History line). 2. no entry for 63450064002.
  3. deadline without holders: 404 02303, logged without values. 4. reduction in the core flow too. 5. every RRI exchange that can carry verification
  data is not printed: contact CREATE/UPDATE with blocks, recursive domain INFO and contact INFO (reply too): `loggable=False` suppresses the reply print as well
  (serial_session/tcp_client), with a test that a verification value never reaches stdout/log; the remaining print of other replies is known debt in
  security.project.md (existing issue #14). 6. MTEST probes as listed.

## Findings (MTEST, 2026-11-28)

- `verificationTimestamp` with `Z` is refused (63200041861), an offset is taken: the proxy sends the instant at `+01:00`. Appendix of rri-extension.md has the fact: **needs the maintainer's confirmation** (a spec appendix edit).
- Valid: name+idcard+auth, email+email_ver_transaction_log+reachability. 63200041867: address+idcard+reachability, email+email_ver_transaction_log+data. 63200041863: a success and a failure of one claim in two blocks.
- A domain of a holder with a failed block: pendingCreate, within seconds serverHold with `verificationDeadlineBeforeDeletion` only. `test6` polls (paced by rpp_requests_per_minute).
- `delay_seconds` in a case is refused by the loader (waits are periods of the facts); the loop is paced by the pacer instead.
- Spec patch example fixed to `/verifications`.
- Contact INFO blocks are `DerivedElement`s in xsdata (xsi:type): unwrapped.

## Check results (code commit ec6f89a, no edits during the runs)

- `PYTHONPATH=src lint-imports`: 32 kept, 0 broken.
- `pytest -n 4 tests/unit`: 3359 passed.
- MTEST reachability case (`domain_availability::test3-a_label`): passed first.
- `pytest -n 4 -m smoke tests/integration`: first run 245 passed, 1 failed, 1 error: `contact_verification/test5` and `message/test1` got a 500 because
  the registry closed the connection ("Connection closed by server", not a proxy defect: both pass alone, 3 passed in 29 s). Second run: 247 passed, 553 skipped, MTEST included.
- `contact_verification/` (6 cases, all smoke) passed on MTEST on its own too.
- Pending: none. Not run: `./test_python_versions.sh` (no change to requirements*.txt; a `pyversions` test was not touched).

## Review round 1 (one medium, two low, all fixed)

1. `_instant`: the RPP mapper (`verification_information.instant`) normalises a lower case `t`/`z`, and refuses an instant that cannot be stated at +01:00 with 400 02005 (`VerificationDateRefused`, no value in the message); the adapter's `_instant` raises a ValueError without the value for a stored one. The generic risk (str(e) in a 500 detail) is already issue #15: commented there with this reproducer instead of a duplicate issue.
2. The base full update, the PATCH of another member and an UPDATE that carries the blocks over are asserted `loggable=False`/not printed.
3. Loops take `max_iterations` (runner, selector check, testing.project.md, unit tests); test6 uses 60. The reduced-view comment claims only the subset.
4. The note on test4: all six `contact_verification/` cases are smoke.

## Check results after review round 1 (commit 2d6c0be... see git log, no edits during the runs)

- lint-imports: 32 kept, 0 broken. Unit: 3372 passed. MTEST reachability case: passed. Smoke incl. MTEST: 247 passed, 553 skipped (contact_verification/ 6 cases included).
