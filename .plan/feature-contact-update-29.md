# Contact update, PUT and PATCH (#29)

Base: stacked on #81 (`feature/domain-put-28`); PR targets `main`, #81 merges first.

## Tasks

- [x] Plan approved by the maintainer
- [x] Failing unit tests, one facet each: EPP update XML, PUT mapper, PATCH mapper (direct and with the current contact), difference, flows, wire
- [x] Models: `ContactUpdate`, `ContactUpdateChanges`, `ContactUpdateChange`, `PostalInfoChange`, `ContactUpdateResponse`, `Contact.status_reasons`
- [x] eppclient: `epp_contacts_Update`, command and response mapping, read of status reasons, empty address members read as absent
- [x] Mappers: `contact_replacement`, `contact_patch`, `contact_difference`; one shared Card-to-Contact conversion with create
- [x] Flows: `flows/contacts.py` (`patch_contact`, `replace_contact`, no-change answer), controller `contacts_update`, `contacts_updatePartial`
- [x] Integration cases `contact_update/`, rewrite `draft_contact/test5-update`
- [x] Docs: `.spec/spec-issues.md`, `architecture.project.md`, `testing.project.md`
- [~] Full `pytest`, draft PR
- [ ] `git rm` this plan, release the mutex

## Findings (evidence)

Probed on the backend with raw EPP (throwaway script in the scratchpad, not in the repo):

- `chg` of `postalInfo` with only `<org></org>` clears the org, and reads back `<org></org>`. The same for `<voice></voice>` and `<fax/>`. The XSD allows it (`org` has no `min_length`, `e164Type` pattern allows the empty string); `name` has `min_length` 1 and `email` too, so they cannot be cleared.
- The backend wipes `sp` and `pc` of the address of a form on ANY `chg` of that form that does not send them again, also when the `addr` is not sent (a `chg` with only `<name>` or `<org>`). RFC 5733 would keep them. So every changed form must be sent complete.
- A `chg` of `postalInfo type="loc"` on a contact without one adds it. Nothing in EPP removes a form.
- An empty `update` or `chg` is `2003`. `add`/`rem` of `status` with a reason works; Info repeats the label as text (#54), as for hosts.
- The read parses empty `sp`/`pc` as `""`, not `None`, which would never equal a wanted address. It has to normalise.
- The draft's own PUT example (json §8.2.4, `draft_contact/test5`) omits `name`, `kind` and `organizations`, and its response keeps them, against core §16.8 ("omitted is cleared, subject to server policy").
- `RPPContact` and the Card classes already refuse undeclared members at any depth (`Undefined.RAISE`).
- A contact has no `due`; `contactStatus.create` allows only the three client labels, so a server label in a PUT is a 400 from the schema.

## Design

PUT: validate with `contact.update`, only members of that schema (400, `02001`), `parse_rpp(RPPContact, {...body, "id": id})` for nested members. The wanted `Contact` comes from the same Card conversion as create (key sequence, US-ASCII, 501 for what EPP cannot hold). The flow reads the contact (Info), takes the difference, sends one `contact:update`, reads back.
PATCH: operations that map to one update go without a read, the rest read the contact, apply the patch to its read representation with `json_patch.py`, parse the patched object with `parse_rpp(RPPContact, ...)` (undeclared members refused, also on the read path), and take the same difference.
Difference: per form (`int`, `loc`) the form is sent complete when anything in it differs. `org`, `voice`, `fax` are cleared with an empty element. Statuses as #28: set replace of client statuses, compare by label, changed reason is rem plus add, `due` is 501. `authInfo` present is always sent, omitted untouched.
No change: 200 with the current contact and no EPP update, 403 (`02201`) for a non-sponsor, compared without regard to case. Failed read-back after an update: 202 without body.

## Decisions

- Stack on #81. Extract the no-change sponsor check into a shared `flows` module and make domains use it in this PR. Use the shared `status_reasons` from `epp_response.py`.
- K: an omitted `name`, address, email or `loc` form is kept on PUT; `org`, `voice`, `fax` are cleared; a sent address replaces the whole one. A PATCH that explicitly removes what EPP cannot clear is 501 (`02102`). spec-issues entry: core §16.8 against the json §8.2.4 response (which keeps `organizations`; we clear it). Rewrite `draft_contact/test5` and say why it differs.
- Every `/contactInfo` PATCH operation reads first. Present `disclose` is 501 (`02102`), omitted left alone. `remove /authInfo` is 501 (`02102`), noted in spec-issues.
- Path id is used as is (as Info and Delete); check a lowercase id on the backend.
- Absence proof: twin contact answers 200 to the same PATCH first.
- PATCH `kind`: unless the patch names `/contactInfo/kind`, `kind` is derived again from the end state (so removing the org does not leave `kind: org`). PUT follows create. Add to spec-issues "Individual contact with an organisation".
- sp/pc defect: note in `testing.project.md`, no issue filed.

## Open questions

(none)

## Review round 1 (PR #83), decisions

- 1: a form in `update.change.postal_info` that `current` lacks and the read-back still lacks (checked on the `Contact` model, presence only) answers 500 (`02400`) naming the form. No split update, no refusal up front. spec-issues: other members of the update may be applied and cannot be undone. Backend defect is pawel-kow/epp#23.
- 2: a wanted `loc` is completed after the keep merge (`after.name or merged.name`, `after.address or merged.address`, then `before`).
- 3: `_loc_change` refuses to clear a name or address of the localization (501).
- 4: the unpatched read goes through `contact_from_rpp` as a baseline; a wanted `loc` equal to the baseline's is replaced by `current.localizedPostalInfo`, unless the `loc` equals the card exactly (follow-the-card). Same for PUT.
- 5: a kept `loc` whose org equals the current card org takes the wanted org.
- 6: direct PATCH raises `NeedsCurrentState` when a status label is already in add or remove. `host_patch` checked, not fixed here.
- 7, 8: tests and docs as listed by the reviewer.

## Corrections

- The probe note that a `chg` of `loc` adds the form was wrong: the backend ignores a `chg` of a form the contact does not have (Info shows no `loc`). A localization cannot be added by an update there; `contact_update/test8` changes an existing one. Filed as pawel-kow/epp#23; noted in spec-issues and testing.project.md. The proxy answers 500 (`02400`), see review round 1.
