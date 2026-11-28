# Plan: RRI contact verification information and the verification process (#251)

Branch `feature/251-rri-verification`, stacked on `feature/250-rri-authinfo-processes` (PR #257) -> #256 -> #255 -> #253. Merge
order #253, #255, #256, #257, this. The spec is committed (90f806d): docs/rri/rri-extension.md, .spec/rri-extension.schema.json,
.spec/spec-issues.md. It is the contract. Mutex `.agent-sync.yml` taken for this branch.

## Tasks

- [x] Read the spec, #250's plan and code, PR #247's entry "Full update of a member an extension adds"
- [~] Plan approved by the orchestrator
- [ ] copy_models.sh: schema into src
- [ ] Generic: `CONTACT_MEMBERS` (`MemberMappers` for the contact), `Contact.extensions` / `ContactReplacement.extensions`, mapper functions take `extensions`, `MemberMappers.split(stated=)`
- [ ] Core of the extension: models (verification information, contact verifications, holder verification, verification process), port, flow
- [ ] RRI part: contact members hook (`RriExtensionPart.contact_members`), XML of the blocks, gateway wiring, refusal codes, verification process INFO
- [ ] Handlers, OpenAPI fragment, preset check, profile leaves
- [ ] Unit tests (mappers, wire, flows, XML, refusals, presets)
- [ ] MTEST integration cases
- [ ] Docs: gap-analysis.md (§3.2, §4.5, Q16 left), architecture.project.md, testing.project.md, rri-5.0-reference.md facts
- [ ] Checks (lint-imports, unit, smoke incl. MTEST), draft PR

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
