# feature/rpp-draft-alignment

Align the proxy to the drafts in `.spec/`, keeping only already-implemented functionality.
Frozen: `src/models/`, `src/eppclient/`, `src/epp_to_model_mapper/`.

## Tasks
- [x] Copy OpenAPI and normalized schema, repoint validator and copy_models.sh
- [x] Open GitHub issues for everything not kept
- [x] Update `rpp_models/` (one class per file) and rewrite the mappers
- [x] Controllers: new operationIds, headers, Problem Details, Table 9 status mapping
- [x] Migrate integration data, add draft examples, extend harness
- [x] Update unit tests and agent docs
- [~] Full pytest run, draft PR

## Decisions (maintainer, 2026-11-04)
- `.spec/` and the `.gitignore` change are committed on this branch.
- OpenAPI copied verbatim; unimplemented operations answer 501 (02101).
- All wire changes in this iteration: media type, header names, 5-digit codes, Problem Details, Location, availability 200/404.
- DELETE answers 200 with an empty body, 01001 when pending.
- Input the frozen model cannot hold: 501 (02102), one full-stack issue.
- PATCH: add/remove with full match on `/nameservers` and `/contacts`, replace on `/registrant` and `/authInfo`, remove on `/registrant`; everything needing a read-and-diff is 501, with an issue.
- Phones are `tel:` on the wire, both ways.
- `kind: individual` with `organizations` is rejected with 501.
- Unclear or impossible spec points go to `.spec/spec-issues.md`.

## Open questions
None.
