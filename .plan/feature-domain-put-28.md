# feature/domain-put-28 (issue #28): domain full update (PUT)

## Tasks

- [x] Plan accepted by the maintainer
- [x] Resolve the nameservers plus DNSSEC difference between PATCH and create (decision 7)
- [x] Tests first: integration cases in `tests/integration/test_case_data/domain_update/` (PUT adds and removes nameservers, contacts, registrant, client status; clears what is omitted; replaces `dns` records and DS; authInfo; no change; missing domain; server status in body; invalid body) and unit tests for the new mapper and flow
- [x] `rpp_to_model_mapper/domain_replacement.py`: `rpp_to_model` (validates `domainName.update`, returns the wanted representation)
- [x] `flows/domains.py`: `replace_domain`
- [x] `controller/domains.py`: `domainNames_update`
- [x] `.spec/spec-issues.md` entry, `docs/agents/architecture.project.md` and `testing.project.md`
- [x] Full `pytest`
- [~] Draft PR, review

## Findings

- `PUT /domainNames/{name}` has `operationId: domainNames_update` in `src/openapi.yaml:6802`, and `controller/domains.py` has no such function, hence the 501 (`02101`).
- The wire contract exists already: request schema `domainName.update` (members `status`, `registrant`, `contacts`, `nameservers`, `dns`, `authInfo`; only `@type` required), response `domainName.read`, 200.
- Core §16.8: PUT sends the complete replacement of the read-write attributes, what is omitted is "cleared or reset to default, subject to server policy", create-only attributes MUST NOT be sent, the server answers 200 with the updated object.
- Host PUT (`flows/hosts.py::replace_host`) is Info, `_difference`, Update, Info. Domain PATCH (#27) already has the difference: `domain_patch_difference.difference(name, current_rpp, patched_rpp)` takes two RPP-form dicts and turns them into a `DomainUpdate`, covering nameservers, hostAttr records, DS/key data, contacts, registrant and client statuses (with reason change as remove plus add). It raises `ValueError` for members outside `CHANGEABLE` that differ, so the read-only members of a read (`provMetadata`, `expiryDate`, `subordinateHosts`, server statuses) must be the same on both sides.
- `patch_statuses.without_server_statuses` / `with_server_statuses` already implement "a client cannot name a server status, and the server ones stay" (spec-issues, "status in JSON Patch").
- `authInfo` is not in the read representation of a domain the client does not sponsor, and `difference` does not handle it (`rpp_to_model_with_current` converts it separately from the operations).
- `patch_domain` answers a no-change patch with the current domain and no EPP update. Host PUT passes the empty update on, the backend answers `2003` (spec-issues, "Full update without a change").

## Decisions (proposed)

1. Reuse `difference`. The wanted representation is `{**current, **<changeable members of the body>}` with the changeable members (`CHANGEABLE` in `domain_patch_difference`) taken only from the body, so an omitted member is cleared and the read-only members equal the current ones. Server statuses are kept as in PATCH, a server status named in the body is 400 (`02001`), `ok` is tolerated. The result is validated with `domainName.read` as in PATCH.
2. No new wire contract: path, schema, status 200 and body as in the OpenAPI. Response is the domain read after the update. A failed read-back after a successful update is 202 with no body, as for PATCH.
3. Errors: a missing domain is the Info error (`02303`, 404). Unsupported pieces are 501 as in create and PATCH (contact label other than admin/billing/tech, `ttl`, non-`authinfo` method, `nameservers` together with records in `dns`).

## Structural changes (need approval)

- New module `rpp_to_model_mapper/domain_replacement.py` (mirror of `host_replacement.py`), exported in `rpp_to_model_mapper/__init__.py`.
- New `replace_domain` in `flows/domains.py` (exported from `flows/__init__.py`), next to `patch_domain`. The `_changes_nothing` and `_read_back` helpers are reused.
- New controller function `domainNames_update` in `controller/domains.py`. No interface change to existing functions, no openapi change.

## Decisions (maintainer, accepted)

1. authInfo omitted in a PUT: left untouched. Present: always sent as `chg`, no comparison. Reason: core §16.8 "subject to server policy", a wipe is irreversible, json §4.9.3 says a client MUST NOT send authInfo, so a PUT built from a read would wipe it. spec-issues entry: §16.8 vs data-objects §11.3.4 vs json §4.9.3, and §4.9.3 vs authInfo in create/update schemas.
2. PUT without a change: 200 with the current domain, no EPP update (as domain PATCH). Host PUT stays (pinned by host_update/test15). Extend spec-issues "Full update without a change" (data-objects §11.3.4, core §16.8; domain 200, host 400 `2003`).
3. Members outside `domainName.update` at the top level, including create-only and read-only ones: 400 `02001` (json §4.4, §4.9.1). Check whether host PUT ignores them, if reproduced file one issue (`bug`, `severity:medium`, `area:spec-compliance`), no fix here.
4. `status` is a set replace: omitted clears all client statuses, a changed reason is remove plus add, server statuses are kept. `ok` or a server status in the body is 400 (the PATCH exception for `ok` does not apply). The wanted object must validate as `domainName.read` also with an empty status array (test).
5. The path name is the only identity, a body `name` is 400 (3).
6. Same `dns`/`nameservers` checks as create, reusing the create code. Add the consequence to spec-issues "DNSSEC with `nameservers`". Unskip `draft_domain/test8-update`.

7. nameservers plus DNSSEC: PUT follows the PATCH rule (only `nameservers` with `ns` records or glue conflict), create stays as is, no issue. spec-issues "DNSSEC with `nameservers`" updated. Covered by `put_nameservers_and_ds`, `put_omitted_dns_removes_ds` and unit tests.
8. Host PUT and read-only members: checked, it does not ignore them (`provMetadata` is a 400, undeclared property), so no issue.

9. Review of PR #81, 11 items, all fixed here (shared `difference` fixes apply to PATCH too): (1) hosts compared across hostObj and hostAttr by lowercase name, a hostAttr with addresses over a host object stays rem plus add; (2) domain read carries status `reason` (wire addition), a reason compared with None is a change; (3) `due` is 501; (4) nested undeclared members are 400 via `RPPDomain`; (5) no-change by a non-sponsor is 403 (`02201`), end to end the backend's Info already answers 2201 for `baz`, so only the unit test reaches our branch; (6) authInfo asserted after PUT; (7) absence proofs show the same match hits first; (8) current delegation read without the glue checks (`checked=False`); (9) `nameservers` with `ns`, `a` or `aaaa` records is 400; (10) `_updated_domain` helper; (11) docs. Real backend: domain Info returns no status reason, a create with hostAttr and no address is `2003`, a PUT without registrant answers 200 and removes it.

10. Round 2 review, 8 items: sponsor compared without case; status `ok` in a PATCH matched by label; current host attributes against other wanted host objects are swapped whole (the reverse keeps the partial change); `domain_update/test32` proves the registrant is gone with a PATCH of `/registrant` and `/status` (422 `02308`); the patched delegation is checked only when `dns` changed; an empty reason is None and a duplicate without a reason does not override one with it; the PATCH nested undeclared members are #82 (not fixed here); `status_reasons` moved to `epp_response.py`.

11. Round 3: current host attributes with any address against wanted host objects are swapped whole too; a later non-empty reason wins over a stored one, a later empty one does not.

## Findings (2)

- PATCH treats nameservers plus DNSSEC differently from create: `domain_patch_difference.difference` rejects only `nameservers` together with `ns` records of `dns` (verified: adding a `ds` record to a domain that has `nameservers` is accepted and yields `add.dnsSEC`), while create (`domains._rpp_to_delegation`) rejects `nameservers` with any `dns.records`. A read of such a domain returns both, so a PUT built from that read would be 400 under the create rule. Asked the maintainer.

## Open questions

1. **authInfo omitted in a PUT.** Core §16.8 says omitted means cleared, but the proxy cannot see authInfo (not readable), so a diff is impossible. Options: (a) omitted leaves authInfo untouched, present replaces it (no destructive surprise, deviates from §16.8); (b) omitted clears it with an EPP null authInfo, as `remove /authInfo` does in PATCH (follows §16.8, but every PUT built from a read, which has no authInfo, wipes the password). Recommendation: (a), with a spec-issues entry. Which one?
2. **PUT that changes nothing.** (a) answer 200 with the current domain without an EPP update (as domain PATCH does), (b) pass the empty update on and answer 400 `02003` (as host PUT does today). PUT is idempotent in HTTP, so recommendation: (a). Host PUT would then differ, I would file an issue for it rather than change it here. OK?
3. **Members in the body that are not in `domainName.update`** (`name`, `provMetadata`, `expiryDate`, `subordinateHosts`, `uName`, `lgr`, `processes`): the schema does not forbid additional properties. Core says the client MUST NOT send create-only attributes. Options: (a) ignore them silently (what host PUT does today), (b) 400 `02001`. Recommendation: (b) for create-only and read-only members, as `reject_set` does for create. Which one?
4. **`status` in the body** with a client status: replaced as a set (client statuses not listed are removed, a changed reason is remove plus add), as the host PUT does. Confirm.
5. A `@type`/name check: the path name is the only identity, a body `name` would be case 3. OK?
