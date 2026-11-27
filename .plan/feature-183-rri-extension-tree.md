# Plan: #183, the RRI extension in the extension tree

Branch `feature/183-rri-extension-tree` from `main` @ 7ea6aba. The later RRI gap PRs (typed messages, discovery and
organisations, AuthInfo processes, verification, release) build on this one (maintainer, 2026-11-27).

No change of behaviour or wire contract. The integration cases do not change.

## Findings

- The extension `de.denic.rpp.rri` is spread over the generic packages:
  - schema `src/rpp/schema/schemas/extensions/rri-extension.schema.json` (copied by `copy_models.sh`), preset
    `src/rpp/schema/schemas/presets/rri.yaml`;
  - request contact: `core/model/request_contact`, `core/ports/request_contact_gateway.py`,
    `core/flows/request_contact`, `rpp/dto/rpp_request_contact*.py`, `rpp/handlers/request_contact`,
    `rpp/mapping/request_contact`;
  - its paths: `rpp/http/extension_paths.py` (`TEMPLATES`: copies of the contact paths);
  - the domain members `generalRequest`/`abuse`: `rpp/mapping/domain/domain_request_contacts.py`, called by
    `domains.py`, `domain_patch.py`, `domain_replacement.py`, `domain_wanted.py`; the transfer input:
    `rpp/mapping/domain/domain_transfer_process.py`;
  - the backends: `RegistryBackend.request_contacts`, with `EppRequestContactGateway` and an `UnsupportedGateway`
    on SQLite;
  - the profile: `settings/profiles/rri.yaml` (`objects`, `extensions`, `domainName.generalRequest`/`abuse`).
- The planets extension shows the target: `register(registry)` with schema, data model, OpenAPI fragment, handlers,
  `backend_parts`, `profile_layer`/`profile_leaves`, presets. `backend_parts` is read only by the SQLite backend.
- The core already holds the request contacts of a domain as contact references with the role `generalRequest` or
  `abuse`, so the core domain model and the RRI domain gateway need no change.

## Design (for approval)

1. **Package `src/extensions/rri/`**, laid out as planets: `core/` (request contact model, port, flows), `rpp/` (dto,
   handlers, mapping, schema with the extension schema and the `rri` preset), `register_rri.py`.
2. **Paths.** The extension's `openapi` builds its fragment from the contact paths of the generated OpenAPI document,
   as `extension_paths.TEMPLATES` does today, so the paths and operationIds stay the same
   (`requestContacts_read`, ...). `TEMPLATES` and its code leave `rpp/http/extension_paths.py`.
3. **Members of a base object.** A generic member mapper registry for the domain name and the domain transfer process
   in `rpp/mapping/domain/` (`DOMAIN_MEMBERS`, `DOMAIN_TRANSFER_MEMBERS`), modelled on the planets'
   `MemberMapper`: the extension registers a mapper that turns `generalRequest`/`abuse` into role references and back.
   `domain_request_contacts.py` moves into the extension. The later PRs use the same registry for the contact
   (`verifications`) and the organisation.
4. **Backend part.** `backend_parts={"rri": "registry_adapter.rri.extensions.rri"}`: the RRI backend loads it as the
   SQLite backend loads its parts and gives the request contact gateway by `extension("de.denic.rpp.rri")`.
   `RegistryBackend.request_contacts`, `EppRequestContactGateway` and the SQLite stub go. The RRI commands and the
   gateway stay in `registry_adapter/rri/`.
5. **Profile.** `requestContact`, the extension id and the `generalRequest`/`abuse` limits move from
   `settings/profiles/rri.yaml` into the extension's `profile_layer`/`profile_leaves`. The preset `rri` and the
   profile's `default_preset: rri` come with the extension.
6. **Configuration.** `rpp_extensions: [extensions.rri]` in `config/backends/rri.yaml`, so every RRI environment
   registers it, and in `deploy/ansible/configs/rri-mtest.yaml.j2` (process rule 5).
7. **Docs.** architecture.project.md (RPP extensions, Registered extensions), copy_models.sh, overview, the issue's
   paths in docs/rri.

## Open questions

- Q1. Package name `extensions/rri` (the issue's) or `extensions/denic_rri`? Proposal: `extensions/rri`.
- Q2. `rpp_extensions` in `config/backends/rri.yaml` or `config/protocols/rri.yaml`? Proposal: backends.

## Tasks

- [~] Plan approved by the maintainer
- [ ] Move the extension into `src/extensions/rri/` and register it (1, 2, 5)
- [ ] Domain and transfer member mapper registry (3)
- [ ] RRI backend part, drop `request_contacts` from the generic backends (4)
- [ ] Configuration and deploy template (6)
- [ ] Tests moved and green: `lint-imports`, unit, smoke incl. MTEST
- [ ] Docs (7)
- [ ] Draft PR

## Checks

Not run yet.
