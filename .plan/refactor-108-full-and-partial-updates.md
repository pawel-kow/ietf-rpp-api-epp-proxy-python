# Plan: keep full and partial updates apart down to the model (#108)

Branch `refactor/108-full-and-partial-updates`, from `main` at `2cd0659`.
Status: **proposal, waiting for the maintainer's acceptance.** No code changes before that.

## Tasks

- [~] T0 Plan, findings and open questions; maintainer accepts the approach
- [ ] T1 Models: `AuthInfoIntent`, `DomainReplacement`, `ContactReplacement`, `HostReplacement` (one file each)
- [ ] T2 Models: `difference` for hosts (moved from `flows/hosts.py` `_difference`), with its tests
- [ ] T3 Models: `difference` for contacts (moved from `rpp_to_model_mapper/contact_difference.py`, EPP refusals split off)
- [ ] T4 Models: `difference` for domains (rewritten from RPP dicts to `Domain` / `DomainReplacement`);
      cases of `test_rpp_domain_patch_current_mapper.py` and `test_rpp_domain_replacement_mapper.py` moved to model level
- [ ] T5 Models: `apply(current, delta)` for the three objects, with round-trip tests
- [ ] T6 EPP side: one derived `replace` orchestration (read unless `current` given → EPP resolution and refusals →
      `difference` → `<update>`, or `unchanged` + `current`)
- [ ] T7 Mappers return intent: PUT → `*Replacement` without a read; PATCH with current → `*Replacement`; direct PATCH → delta
- [ ] T8 Flows and controllers: `patch_*` / `replace_*` call `update(delta)` or `replace(wanted, current)`; sponsor 403 kept
- [ ] T9 Docs: `architecture.project.md` (mapper and flow sections), `spec-issues.md` only if wording names moved modules
- [ ] T10 Full `pytest` (unit + EPP integration) unchanged and green; draft PR

## Findings (evidence)

1. Three differences today, at two levels:
   `rpp_to_model_mapper/domain_patch_difference.py:difference` (RPP dicts),
   `rpp_to_model_mapper/contact_difference.py:difference` (models, raises `NotSupportedByEpp`),
   `flows/hosts.py:_difference` (models).
2. Domain PUT reads in the mapper path: `controller/domains.py:101-108` passes `rpp_to_model_with_current`, which
   merges the body with the read dict (`domain_replacement.py:rpp_to_model_with_current`).
3. Contact PUT is EPP-flavoured in the mapper: `contact_replacement._keeping_what_epp_cannot_clear` keeps an omitted
   name, address, email and localization (spec-issues "Full update of a contact"), while a PATCH that removes them is
   501 (`contact_difference._int_change` etc.). So PUT and PATCH differ for the same "absent" value.
4. Host PUT that changes nothing **sends** the empty update and the backend answers `2003` (spec-issues "Full update
   without a change"); host PATCH that changes nothing returns the current host **without** a sponsor check
   (`flows/hosts.py:patch_host`). Domains and contacts short-circuit with `require_sponsor` in both.
5. Domain dns of the current state is converted with `checked=False` (`domain_patch_difference._delegation`), and the
   wanted dns only when it differs from the read (`checked=patched.get("dns") != current.get("dns")`). A PUT mapped
   without a read cannot know whether its dns repeats the stored one.
6. `is_client_label` lives in `rpp_to_model_mapper/patch_statuses.py`; model-level differences need it, and
   `models/` must not import a mapper.
7. Contact flow checks for a lost `postalInfo` form after the read-back (`flows/contacts.py:_lost_form`), from the delta
   and `before`. This is EPP-specific (pawel-kow/epp#23).
8. `docs/rri/refactoring.md` (§3.5, §3.6) exists only on `feature/denicrri`; it names the later module
   `registry/derived_update.py` and the model files `models/<object>_difference.py`, `models/<object>_application.py`.

## Proposed design

- **Model types** (new files in `models/`):
  - `AuthInfoIntent` — `KEEP`, `SET(auth_info)`, `CLEAR`. Domain PUT without `authInfo` = `KEEP`; PATCH
    `remove /authInfo` = `CLEAR` (domains only; contacts stay 501).
  - `DomainReplacement(name, ns: NS | None, registrant, contacts, dnsSEC, status, status_reasons, auth_info)`.
  - `ContactReplacement(id, name, organisationName, email, phone, fax, address, localizedPostalInfo, status,
    status_reasons, auth_info)` — see Q2 for omitted members on a PUT.
  - `HostReplacement(name, new_name, ipv4, ipv6, status, status_reasons)`.
- **Pure functions** in `models/`: `domain_difference.py`, `contact_difference.py`, `host_difference.py`
  (`difference(current, wanted) -> *Update`) and `domain_application.py`, `contact_application.py`,
  `host_application.py` (`apply(current, delta) -> *Replacement`). `difference` is neutral: it can express
  "clear name" etc.; the EPP side refuses that. `is_client_label` moves to `models/` (re-exported from
  `patch_statuses` so mapper callers stay).
- **EPP derivation**: one module, `flows/derived_update.py`, one generic orchestration
  `replace(read, resolve, difference, update, wanted, current=None) -> ReplaceOutcome | ErrorResponse`
  used by the three flows; per-object EPP resolution (contact KEEPs, `with_stored_localization`) and refusals
  (EPP cannot clear name/address/email/localization; `ds` + `dnskey` added together) in
  `flows/epp_<object>_replacement.py`. Refusals return `ErrorResponse` with the same code (`02102`/`02103`) and the
  same detail text as today, rendered by `raise_epp_error` (see Q1).
- **Flows**: `patch_domain(update | None, wanted_from_current)`, `replace_domain(wanted)`; the same for contacts and
  hosts. `ReplaceOutcome.unchanged` + `current` → `require_sponsor` (domains, contacts). Hosts keep finding 4 as is.
- **Mappers**: `domain_replacement.rpp_to_model` → `DomainReplacement` (no `_with_current`);
  `domain_patch.rpp_to_model_with_current` → `DomainReplacement` (keeps `_reject_other_changes`, the
  `nameservers`/records refusal and the `checked` decision, which need the read dict). `domain_patch_difference.py`
  and `rpp_to_model_mapper/contact_difference.py` go away. Same pattern for contacts and hosts.

## Must not change (from #108)

EPP commands per request, including `hostObj` vs `hostAttr` kept apart and refused together; changed reason →
remove + add; per-host glue address changes; refusal of changes outside `CHANGEABLE`; command count (direct PATCH =
update + info, others = info + update + info). Also: HTTP status, `RPP-Code` and Problem detail text of every refusal.

## Open questions

- **Q1** Where does the EPP derivation live until `registry/` exists? Proposal: `flows/derived_update.py`, refusals
  as `ErrorResponse` (no exception crossing from flows into the controller's `map_request`). Alternative: keep raising
  `NotSupportedByEpp` and catch it in the controller.
- **Q2** Contact PUT omitting name/address/email/localization (finding 3). Proposal: the PUT mapper sets those members
  to `KEEP` in `ContactReplacement` (as `auth_info`), so "omitted = clear" holds for the model and the PUT policy of
  spec-issues stays explicit; the EPP side resolves `KEEP` against `current` (including `_kept_localization` and
  `_complete_localization`). Alternative: an origin flag (PUT/PATCH) on the replacement.
- **Q3** Domain PUT dns without a read (finding 5): a PUT that repeats stored out-of-zone glue passes today and would
  be refused. Accept this edge, or keep a `checked` decision by letting the EPP side re-check dns against `current`?
- **Q4** `with_stored_localization` is a consequence of how RPP renders a localization, not of EPP. #108 moves it to
  the EPP side; keep it in the mapper path instead?
- **Q6** Domain/contact PUT without `authInfo`: stays `KEEP` (spec-issues: json §4.9.3 forbids sending it, so C1's
  rule would wipe the password on every PUT of a read), or becomes `CLEAR`?
- **Q7** Host PUT/PATCH that changes nothing by a non-sponsor: 403 via `require_sponsor` as domains/contacts, or 200?
- ~~**Q5**~~ Decided, D2. Host PUT that changes nothing (finding 4): keep sending the empty update (`2003`), as "must not change"
  requires? Then `replace` takes a flag to send even when unchanged, for hosts only.

## Decisions

- **D1 (Q1)** Flows return typed results or `ErrorResponse` only; they raise nothing HTTP and import no web
  framework (checked: `src/flows/*.py`). EPP refusals in the derivation follow that: `ErrorResponse`, rendered by
  `raise_epp_error`. Pending maintainer confirmation.
- **D2 (Q5)** A host PUT that changes nothing sends no update and answers 200 with the current host, as domains and
  contacts. Behaviour change: `spec-issues.md` "Full update without a change", host integration case(s) and
  `test_host_flows.py` updated.

## Corrections

- **C1 (Q2)** A PUT is the wanted state: after it, the read-write members of the object equal the request. An omitted
  contact name, address, email or localization means "clear", as for the organisation and the numbers. EPP cannot
  clear them, so the EPP side refuses with 501 (`02102`), as a PATCH that removes them does today. `KEEP` for these
  members and `_keeping_what_epp_cannot_clear` / `_kept_localization` go away. Behaviour change: `spec-issues.md`
  "Full update of a contact", `contact_update/test5-put_keeps_what_epp_cannot_clear`, `test9-put_keeps_the_localization`,
  `draft_contact/test5-update` (the json §8.2.4 example omits `name` and becomes 501) and the replacement mapper tests.
  Open: does `authInfo` on PUT stay `KEEP` (Q6)?
