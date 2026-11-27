# Plan: feature/249-rri-organisations (#249, closes #99)

Stacked on `feature/248-rri-typed-messages` (PR #255, ready, unmerged), which is stacked on `feature/183-rri-extension-tree`
(PR #253). Merge order: #253, #255, then this PR. The spec is approved and committed (5fb86e2: `docs/rri/rri-extension.md`,
`.spec/rri-extension.schema.json`, `.spec/spec-issues.md`); it is the contract. The PR says "Closes #249" and "Closes #99".

## Decisions settled before the plan (maintainer/orchestrator)

- Discovery `objects`: `message` on EPP and RRI, `organisation` on RRI, and the objects of the offered extensions. SQLite: only if it
  serves messages (it does, see findings; confirm below).
- `GET /organisations/{id}` on RRI = regacc INFO, any authenticated client, mapped as the appendix "Mapping of regacc INFO" of
  `rri-extension.md` says. Errors: 63310062008 -> 400 `02005`, 63300062010 -> 404 `02303`. Create, update, delete, users, processes:
  501 `02101` on RRI. EPP and SQLite: organisations stay 501.
- Templates are members the rri extension adds to the organisation, through a generic member registry analogous to `DOMAIN_MEMBERS`;
  no RRI name in generic code.
- The organisation read model is a generic core model and port (`organisations` gateway of the backend).
- Never 500 on registry data the client cannot fix; log field names, never values.
- Gap analysis (§3 table row "regacc INFO") and `architecture.project.md` are updated; Q10 stays as PR #247 has it.

## Findings (evidence)

- MTEST is reachable from here (`domain_availability::test3-a_label` passed, 1 passed): the smoke run covers it.
- No handler serves `organisations_*` today: every `/organisations...` request answers 501 `02101` (`resolver_error=501`). `organisation` is
  not in `DRAFT_OBJECTS` (`rpp/http/extension_paths.py`), so `PresetMiddleware` never checks it against the profile and the
  `rpp_openapi_omit_unheld_objects` switch never omits its paths.
- Profile `objects`: `epp.yaml` = domainName, host, contact; `rri.yaml` = domainName, contact (the rri extension adds requestContact);
  `sqlite.yaml` = [] (extensions add theirs). `message` has no collection, so `PresetMiddleware` ignores it; nothing else reads `objects`
  except discovery, `domains.py` ("host" in objects) and the test selector `profile.objects`.
- SQLite serves messages (`SqliteMessageGateway`, `planet_message/` cases), so `message` belongs in its `objects` too.
- regacc INFO is in the generated models already: `RegistryRequest(info_2=regacc.Info(handle=...))`, reply `regacc.InfoData`
  (`handle, name, postal{address[], postalCode, city, countryCode}, phone[], fax[], email, url[], memberacc, contact[] {role,
  uri-template, changed}, changed`). `registry_adapter/rri/result_codes.py` maps 63300062010 to `OBJECT_DOES_NOT_EXIST` already;
  63310062008 falls to class 6 -> `PARAMETER_VALUE_POLICY_ERROR` (422), so it needs an entry.
- Real MTEST values (probed with a throwaway script, nothing created; own RegAcc DENIC-54321, other DENIC-99995, plus DENIC-1):
  - `handle` is returned as stored in upper case, also when asked in lower case (`denic-99995` is found).
  - phone/fax are E.123 with blanks: `+49 69 27 235 0`, `+49 69 27235 290`; DENIC-99995 has two fax numbers; no numbers of other shapes seen.
  - `url`: `https://www.denic.de`, `http://www.nic.de`; one each.
  - `memberacc` equals `handle` for all three (so `parent` is omitted); a foreign memberacc was not seen.
  - `contact` holds `generalrequest` (all three) and `abusecontact` (DENIC-54321 only), each `type REQUEST`, `uri-template`
    `mailto:...`, `changed` with an offset (`+02:00`, `+01:00`).
  - `changed` of the RegAcc has an offset too (converted to UTC as everywhere, `rri_time.utc_time`).
  - An address may have 1 or 2 `regacc:address` lines.
  - Errors: `DENIC-999999999` (well-formed, unknown) -> 63300062010; `DENIC-999999999999` and `DENIC-` + 26 nines -> 63310062008;
    `DENIC-0`, `DENIC-99995-RRI`, `NOTAHANDLE` -> 83000000004 (XSD failure, already 400 `02005` through #233). The session stays usable.
- `Address` (`core/model/contact/address.py`) is what the contact model holds; `rpp/mapping/contact/phones.py` converts the dotted
  `+CC.number[xEXT]` to a tel URI; `RPPCard` and its parts are the DTOs; `links` is a free dict.
- `MemberMappers` (`rpp/mapping/shared/member_mappers.py`) needs `merge` and a `to_model` for a request; an organisation has only
  read-only members, so neither is used.

## Approach

### 1. Core (generic)
- `core/model/organisation/organisation.py`: `Organisation(id, up_date, parent, name, address, phones, faxes, email, urls, extensions)`.
  `address` is the contact model's `Address`; `phones` and `faxes` are lists of the dotted form (`+49.69272350`, `+49.1234x12`) the
  adapter converted; `urls` a list; `parent` the id of the member as a plain string (None when absent); `extensions` maps the id of an
  extension to a typed object of its own core (as the planets do). `status` and the role are the RPP mapper's constants for a
  registrar (nothing the model holds); see the open question on where the constants live.
- `core/ports/organisation_gateway.py`: `OrganisationGateway.info(id, client_transaction_id=None) -> OperationResponse[Organisation] | ErrorResponse`.
- `RegistryBackend.organisations: OrganisationGateway`.
- No flow: a read is a gateway call, as the host and contact reads (handler -> gateway).
- import-linter: `core.model.organisation` may import `core.model.contact` (the `Address`), like `domain -> contact` today; the contract
  and `architecture.project.md` "Dependency rules" say so. (Alternative: move `Address` to `model/shared`; I recommend against the churn.)

### 2. RRI adapter
- `registry_adapter/rri/commands/organisation/info.py`: `rri_organisation_info(client, handle, ctid, parts)`: `run(... info_2=Info(handle=...), write=False,
  payload_of=data_of(InfoData))`, then `organisation_from_rri(data, parts)` in `common.py`:
  - `id` = `handle`; `up_date` = `utc_time(changed)`; `parent` = `memberacc` unless equal to the handle (case-insensitive);
  - `address` from `postal` (`address[]` -> street lines, `city`, `postalCode`, `countryCode`);
  - `phones`/`faxes`: E.123 -> dotted: the digits before the first separator (blank, `-`, `.`, `/`) are the country code, the digits before
    an `x` the subscriber number, those after it the extension; a number that gives no `+CC.number` of 1-3 and 1-14 digits (and 15 in all) is
    left out, its field name logged (`phone`/`fax`), never the value;
  - `urls`: each `regacc:url` with a scheme (`^[A-Za-z][A-Za-z0-9+.-]*:`), the rest left out and logged by field name;
  - `extensions`: for each extension part with an organisation member hook, `extensions[part.extension_id] = hook(data)`.
- `RriExtensionPart` gains `organisation_members: Callable[[InfoData], object] | None` (module attribute `ORGANISATION_MEMBERS`, loaded by name like
  `MESSAGE_TYPES`); the generic gateway never names the extension.
- `registry_adapter/rri/gateways/rri_organisation_gateway.py`: `RriOrganisationGateway(client, parts)`, `info` only; `RriBackend.organisations`.
- `registry_adapter/rri/extensions/rri/organisation_members.py`: `ORGANISATION_MEMBERS` builds `RegistrarRequestTemplates(general_request, abuse)`
  from the `contact` entries by `role` (`generalrequest`, `abusecontact`); an entry without `uri-template` is left out; `changed` -> UTC.
- `result_codes.py`: `63310062008 -> PARAMETER_VALUE_SYNTAX_ERROR` (400 `02005`).
- EPP: `EppOrganisationGateway` (every command `UNIMPLEMENTED_COMMAND`, as `RriHostGateway`); SQLite: `UnsupportedGateway("organisation")`.

### 3. Extension core and RPP side of the rri extension
- `extensions/rri/core/model/registrar_request_templates.py`: `RequestTemplate(uri_template, up_date)`, `RegistrarRequestTemplates(general_request, abuse)`.
- `rpp/mapping/organisation/organisation_members.py` (generic): `ORGANISATION_MEMBERS = MemberMappers(merge=...)`; `MemberMapper.to_model` is
  documented as optional for a read-only member (never called: a definition without the member refuses it first). `MemberMappers` is not
  changed otherwise.
- `extensions/rri/rpp/mapping/request_template_members.py`: `RequestTemplateMembers` (`members = ("generalRequestTemplate", "abuseTemplate")`,
  `to_rpp(organisation)` from `organisation.extensions[EXTENSION_ID]`), added in `register_rri` (`ORGANISATION_MEMBERS.add(...)`).
- Copy the schema into src with `copy_models.sh`; the 3 failing doc tests then pass.

### 4. RPP side (generic)
- `rpp/dto/rpp_organisation.py` (+ `RPPOrganisationRole`, `RPPOrganisationReference`; the existing `RPPStatus` and `RPPProvMetadata` are reused).
- `rpp/mapping/organisation/organisations.py`: `model_to_rpp(organisation, extensions=())`: `id`, `provMetadata {spClientId = id, upDate}`,
  `status [ok]`, `roles {registrar {status [ok]}}`, `parent`, `contactInfo` Card (`kind org`, `name.full`, one `addr`, `voice`, `voice-1`..,
  `fax`, `fax-1`.. with feature `fax`, `email`, `url`, `url-1`..), then the members of the extensions, then `validate_schema("organisation.read", ..., extensions=extensions)`.
  Optional Card entries that fail their definition are left out, never a 500 (see open question 3).
- `rpp/handlers/organisation/organisation_handlers.py`: `organisations_read(id)`: `requested_elements("organisation")`, `get_backend().organisations.info`,
  `raise_registry_error`, `include_elements.visible`, `response_profile().extensions`; exported in `rpp/handlers/__init__.py`. Create, update,
  updatePartial, delete, processes: no handler (501 `02101`, as today).
- `organisation` joins `DRAFT_OBJECTS`, so the middleware checks it against the profile (see open question 1).

### 5. Profiles and discovery
- `epp.yaml`: `message` added to `objects`; `rri.yaml`: `message`, `organisation`; `sqlite.yaml`: `message` (see open question 2).
  Discovery reads the profile, so `Discovery` and the mapper are unchanged; #99 is done by this.
- Docs: `docs/rri/gap-analysis.md` (§3 row regacc INFO: implemented, `/organisations/{id}` read; the Q10 text is left), the `Proxy (RRI, planned)` lines of
  `spec-issues.md` lose "planned" (implemented), `docs/agents/architecture.project.md` (structure, dependency rule, extension member registry, discovery
  `objects`, the organisation read, `testing.project.md` where the selectors or cases are named), `docs/rri/rri-extension.md` not touched (approved).

### 6. Tests
- Unit: regacc INFO XML -> `Organisation` (fake client: fields, phones in each E.123 shape and the left-out ones, urls with and without scheme,
  `parent` omitted and set, templates by role, a template without URI left out, offsets to UTC); the mapper (full read, base preset without the
  templates, `rri` preset with them, a failing optional entry left out); wire (200, `includeElements`, 400 `02005` for 63310062008, 404 for
  63300062010, 83000000004 -> 400, 501 `02101` for create/update/delete/users/processes on RRI, 501 on EPP and SQLite); discovery `objects` per backend;
  `63310062008` in the result-code table; import-linter contracts.
- Integration (`organisation_read/`, cases for MTEST selected by `profile.objects` contains `organisation`): the own RegAcc and the other one
  (`{prefix}` of the registrars gives their RegAccIds; to be checked how a case names a RegAccId), `parent` absent, the templates under the `rri`
  preset, 404 for an unknown RegAcc, 400 for a well-formed id the registry refuses; smoke-marked where cheap (one read = one RRI request). The discovery
  cases (`draft_discovery/test1`, `demo_discovery`, `sqlite_drafts_objects/test5`) expect `message` (and `organisation`).
- Checks: `lint-imports`, `pytest -n 4 tests/unit`, `pytest -n 4 -m smoke tests/integration` (includes MTEST), with progress visible.

## Tasks

- [~] Plan pushed, checkpoint 1 reported.
- [ ] Copy the schema (`copy_models.sh`); core model, port, backend attribute; import-linter contract.
- [ ] RRI adapter: command, conversions, gateway, extension hook, result code; EPP and SQLite gateways.
- [ ] RPP: DTOs, mapper, member registry, rri extension mapper, handler, `DRAFT_OBJECTS`.
- [ ] Profiles and discovery; docs.
- [ ] Unit tests; integration cases; checks; draft PR (checkpoint 2).

## Open questions (with recommendation)

1. **`organisation` in `DRAFT_OBJECTS`.** Adding it makes EPP and SQLite answer `/organisations...` 501 `02307` ("no organisation object on this
   server", as the unheld objects of the profile do) instead of 501 `02101`, and makes `rpp_openapi_omit_unheld_objects` leave the paths out
   there. Status stays 501. Recommendation: add it (the profile and discovery then say the same as the routing). If a wire code must stay `02101`
   on EPP/SQLite, I leave it out and the middleware does not guard organisations.
2. **`message` in the SQLite profile.** SQLite serves messages, so discovery should list it. Recommendation: yes, `objects: [message]` in
   `sqlite.yaml`. The planets demo configs' discovery cases get it too.
3. **Registry data that fails the RPP schema.** I propose to leave an optional Card entry that fails its definition (a link that is no URI, an
   email or phone that fails its format, a template that fails `requestTemplate`) out of the response and log its field name, and to answer
   500 only for a response that still fails (required members: `id`, which the registry guarantees). Recommendation: as proposed.
4. **Where the constants of the registrar organisation live** (`status ok`, role `registrar` with status `ok`, `spClientId = id`). They are
   facts of "an organisation read from registrar data", not of RRI as such. Recommendation: the model holds `status: list[str]`
   and `roles: dict[str, list[str]]`, which the RRI gateway fills (`["ok"]`, `{"registrar": ["ok"]}`), so the RPP mapper stays generic and a later backend states
   its own; `spClientId` is `Organisation.sponsor_id`, which the RRI gateway fills with the handle.
5. **No precheck of the handle in the proxy.** RRI answers a malformed handle 83000000004 (400 `02005` with its message as detail) and a numeric
   overflow 63310062008, both at the cost of one INFO. Recommendation: no precheck (the registry's format is its own; I did not verify
   whether a refused INFO counts against the quota); say if a regular expression of the proxy is wanted.
6. **`includeElements` on an organisation** needs the Visibility of the data elements from the data-objects model; `organisation` is in the model, so
   it works as for domains. No question, noted.

## Decisions recorded from the orchestrator

(none yet)
