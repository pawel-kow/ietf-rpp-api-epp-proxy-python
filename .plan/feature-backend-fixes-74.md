# Follow up on backend fixes (#74), spec notes (#75, #76)

Branch `feature/backend-fixes-74` from `main` 2da9bfc. Scope is the body of #74, plus moving #75 and #76 to
`.spec/spec-issues.md` and closing them. PR #73 is open and touches the same test groups, so new case numbers
start after its numbers (`domain_update` 16, `host_update` 32).

## Tasks

- [~] 1. Harness: `any_of` alternatives in a step's `response`, list comparison that does not depend on sort order, unit tests
- [ ] 2. Cases using it: `domain_create/test16`, `test17`, `test18`
- [ ] 3. `contact_create/test20`: renamed, 201 with the localization read back
- [ ] 4. New integration cases: `replace /dns` with `ds`, duplicate host address, unknown user, repeated `RPP-Cltrid`
- [ ] 5. Remove workarounds: `_addresses`, `errors='replace'`
- [ ] 6. Docs: `testing.project.md`, `RPP_IMPLEMENTATION_NOTES.md`, docstring, `spec-issues.md` (#75, #76)
- [ ] 7. Full `pytest`, draft PR closing #74, #75, #76

## Decisions

- `any_of` only, no "end the case" flag from #74: a create answers with the object from a follow-up Info, so one
  step checks both the rejection and the key material. #74 allows "the response or a GET".
- A `ds` given back for a `dnskey` is checked by type and algorithm only. Its digest depends on the random domain name.
- Both "optional" workarounds in #74 are removed, in their own commit so that it can be dropped.

## Findings

- Trial on a copy of `main` (see #74): the removals pass once the fixtures use `ip="v4"`/`"v6"`.
- `recusive_compare_existing` sorts both lists and pairs by position, which mispairs a partial expected element.
