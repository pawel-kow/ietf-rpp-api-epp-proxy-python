# feature/domain-put-28 (issue #28): domain full update (PUT)

## Tasks

- [~] Plan accepted by the maintainer
- [ ] Tests first: integration cases in `tests/integration/test_case_data/domain_update/` (PUT adds and removes nameservers, contacts, registrant, client status; clears what is omitted; replaces `dns` records and DS; authInfo; no change; missing domain; server status in body; invalid body) and unit tests for the new mapper and flow
- [ ] `rpp_to_model_mapper/domain_replacement.py`: `rpp_to_model` (validates `domainName.update`, returns the wanted representation)
- [ ] `flows/domains.py`: `replace_domain`
- [ ] `controller/domains.py`: `domainNames_update`
- [ ] `.spec/spec-issues.md` entry, `docs/agents/architecture.project.md` and `testing.project.md`
- [ ] Full `pytest`, draft PR

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

## Open questions

1. **authInfo omitted in a PUT.** Core §16.8 says omitted means cleared, but the proxy cannot see authInfo (not readable), so a diff is impossible. Options: (a) omitted leaves authInfo untouched, present replaces it (no destructive surprise, deviates from §16.8); (b) omitted clears it with an EPP null authInfo, as `remove /authInfo` does in PATCH (follows §16.8, but every PUT built from a read, which has no authInfo, wipes the password). Recommendation: (a), with a spec-issues entry. Which one?
2. **PUT that changes nothing.** (a) answer 200 with the current domain without an EPP update (as domain PATCH does), (b) pass the empty update on and answer 400 `02003` (as host PUT does today). PUT is idempotent in HTTP, so recommendation: (a). Host PUT would then differ, I would file an issue for it rather than change it here. OK?
3. **Members in the body that are not in `domainName.update`** (`name`, `provMetadata`, `expiryDate`, `subordinateHosts`, `uName`, `lgr`, `processes`): the schema does not forbid additional properties. Core says the client MUST NOT send create-only attributes. Options: (a) ignore them silently (what host PUT does today), (b) 400 `02001`. Recommendation: (b) for create-only and read-only members, as `reject_set` does for create. Which one?
4. **`status` in the body** with a client status: replaced as a set (client statuses not listed are removed, a changed reason is remove plus add), as the host PUT does. Confirm.
5. A `@type`/name check: the path name is the only identity, a body `name` would be case 3. OK?
