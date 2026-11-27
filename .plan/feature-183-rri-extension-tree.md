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

## Maintainer addition (2026-11-27)

The rri extension also brings an RPP Profile (registered via `profiles` of its `RegisteredExtension`, like the planets profiles
`rocky-planets` and `catalogued-satellites`) that limits: the use of host objects (no host references in the `nameservers` of a
domain, no `/hosts` objects), contact labels other than `registrant` on the domain name, and requires at least one registrant.
- The spec writer writes `docs/rri/rri-profile.md`, `.spec/rri-profile.schema.json` and the preset text, and commits them on
  this branch after the move; the coder does not write them. The coder then implements the registration.
- **Decided (maintainer): the profile is NOT bound to the `rri` preset.** The extension brings a second preset, proposed name
  `rri-strict` (final name comes with the spec text) = the `rri` preset with the profile bound. `rri` stays unchanged and the
  default, so the wire contract of `rri` does not change; only requests under the new preset get 422 `02308` for violations.
- The move stops at a checkpoint before the full checks, so the spec writer can add the profile spec.

## Decisions (orchestrator, for the maintainer), spec writer's commit 243770d

- Profile `de.denic.rpp.profile.rri` 1.0 ("DENIC RRI profile", requires `de.denic.rpp.rri`), preset `de.denic.rpp.preset.rri-strict`
  1.0 = base preset `rri` + this profile, no extension of its own. The `rri` preset is unchanged and stays the default.
- Profile Schema: `required: [registrant]`, `contacts[].label` enum `[registrant]`, `nameservers: false`, on domainName.create and update.
- Host operations keep 501 under every preset.
- Implementation findings: the profile (step 2) runs before the mapper, so a `generalRequest`/`abuse` label under `rri-strict` is
  422 02308, not 501 02102; the profile does not constrain `domainName.read`, so a patch that needs the current state is not
  checked on the patched object (a `remove /registrant` is sent). `rri-strict` is registered, but offered by no configuration
  (offering it adds it to the discovery lists that the integration cases state in full): a server lists it in `presets`.

- The preset `rri` states no `url` (its spec document gives one, rri-preset.md): adding it changes the wire form, which
  tests/unit/test_presets_wire.py pins; left out, to the orchestrator.

## Open questions

- Q1. Package name `extensions/rri` (the issue's) or `extensions/denic_rri`? Proposal: `extensions/rri`.
  **Decided (maintainer): `src/extensions/rri/`.**
- Q2. `rpp_extensions` in `config/backends/rri.yaml` or `config/protocols/rri.yaml`? Proposal: backends.
  **Decided (maintainer): `rpp_extensions: [extensions.rri]` in `config/backends/rri.yaml`, and in the deploy template
  `deploy/ansible/configs/rri-mtest.yaml.j2` (process rule 5).**

## Decisions made while implementing

- Orchestrator: the plan is approved, no plan checkpoint; paths, operationIds, status codes, schemas and the integration
  cases stay as they are.
- `RegisteredExtension.openapi` takes the OpenAPI document of the drafts (so the rri fragment can be built from the contact
  paths); the planets fragments ignore it. The rri operationIds stay `requestContacts_read` ...: the operations carry
  `x-openapi-router-controller` (the handler module), which the resolver reads, so the served documents keep the names.
- The request contact commands and gateway move to `registry_adapter/rri/extensions/rri/` (as the SQLite parts are in
  `registry_adapter/sqlite/extensions/<name>`), because a generic part of an adapter may not import an extension.
- The leaves `domainName.generalRequest.*` and `domainName.abuse.*` leave `LEAVES`, `epp.yaml` and `sqlite.yaml`. A test selector
  on a leaf an in-repository extension adds reads None on a profile without the extension (as a null fact), so the cases that
  select on them still skip on EPP and SQLite.

## Tasks

- [x] Plan approved by the maintainer
- [x] Move the extension into `src/extensions/rri/` and register it (1, 2, 5)
- [x] Domain member mapper registry (3): one registry `DOMAIN_MEMBERS`; the transfer request converts its domain data as a create, so it uses the same mappers
- [x] RRI backend part, drop `request_contacts` from the generic backends (4)
- [x] Configuration and deploy template (6)
- [ ] Tests moved and green: `lint-imports`, unit, smoke incl. MTEST
- [ ] Docs (7)
- [x] The rri profile and preset `rri-strict` (maintainer addition, below), registered after the spec writer's text is on the branch
- [ ] Draft PR

## Checks

On the final commit, in the order of process.project.md:
1. `PYTHONPATH=src lint-imports`: 31 kept, 0 broken.
2. `pytest -n 4 tests/unit`: 3039 passed.
3. `pytest -n 4 -m smoke tests/integration`: 232 passed, 488 skipped, 0 failed.
4. MTEST probe (`rri-mtest domain_availability test3-a_label`): passed, MTEST reachable, so the smoke run of step 3 covered MTEST.
5. Not applicable (requirements and pyversions tests unchanged).
Deploy template changed: `ansible-lint` in deploy/ansible: passed, 0 failures, 0 warnings (run from a scratch venv, ansible-lint
was not installed); `ansible-playbook --syntax-check site.yml`: OK (warnings about no inventory only);
`docker build -f deploy/docker/Dockerfile .`: built.
