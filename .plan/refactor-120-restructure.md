# Plan: restructure src/ into core, rpp and registry adapters (#120, phases 2-6)

Branch `refactor/120-restructure`, one draft PR for phases 2 to 6 (maintainer). Behaviour does not change: every phase
ends with `PYTHONPATH=src lint-imports` and the full `pytest -n 8`, and is its own commit.

## Tasks

- [x] T0 Move tool (scratchpad): moves modules and rewrites every import in `src/` and `tests/` as an absolute import
      from the defining module; star imports become the names used
- [x] T1 Phase 2: `eppclient`, `epp_to_model_mapper`, `helpers` → `registry_adapter/{epp,common}`; `ns_map` passed in;
      `commands/not_used/` deleted; contracts renamed
- [x] T2 Phase 3: `models`, `registry`, `flows` → `core/` per object; explicit imports; `BackendProfile` and the
      refusals → `core/capabilities`
- [x] T3 Phase 4: `controller` → `rpp/http` + `rpp/handlers`; mappers and schema validator → `rpp/`; session pool →
      `core/session`; `run.py` → `main.py`; `copy_models.sh`, Dockerfile and docs for `uvicorn main:app`
- [x] T4 Phase 5: `IdnTables` → `epp/`; read-back once (closes #17); settings passed in
- [x] T5 Phase 6: result envelope for gateway results
- [~] T6 Docs (`architecture.project.md`, `testing.project.md`, `process.project.md`, README), import-linter contracts
      for the target, final checks, draft PR

## Findings (evidence)

1. 230 modules outside the generated packages; tests import them by module path in 71 test files.
2. Star imports outside `__init__`: `controller/{domains,contacts}.py`, `eppclient/epp_{domains,contacts}.py`,
   `epp_to_model_mapper/{domains,contacts}.py`, `app.py`.
3. `epp_to_model_mapper/commands/helper.py:25` renders with `config.rpp_epp_ns_map`; the XML tests assert the prefixes
   of that map (`domain:`).
4. `RelativeResolver('controller')` resolves an operationId as an attribute of the package, so the handlers package
   keeps re-exporting the handlers.
5. `models/contacts.py:52` defines a second `ErrorResponse`, besides `models/response.py`.

## Decisions

- D1 (maintainer) Phases 2-6 in one draft PR, without acceptance between phases.
- D2 Package `__init__` files are empty, except `rpp/handlers`, whose functions connexion resolves by name (finding 4).
- D3 Imports are absolute.
- D4 `epp/commands/<object>/` keeps today's three layers as three modules: `epp_request.py` (the xsdata request),
      `<object>_xml.py` (render, parse), `<object>_commands.py` (one operation: render → send → parse). Shared reply
      parsing in `epp/commands/shared/`.
- D5 `ns_map` goes into an `EppCodec` built by the composition root, held by `EppBackend` and passed to the commands.
- D6 `ns_map` is passed as a plain dict: `EppBackend(epp_client, ns_map)` → gateways → `epp_*` commands → `*_xml` →
      `epp_to_str(epp, ns_map)`, keyword-only where added. The composition root passes `config.rpp_epp_ns_map`; the
      tests pass `tests/helper/epp_ns_map.EPP_NS_MAP`, the same map.
- D7 `registry_adapter/common` must not know its protocol: `EPP_READ_TIMEOUT` → `READ_TIMEOUT`, the docstrings no
      longer name EPP, and the warning that names `rpp_epp_tls_insecure_skip_verify` moves to the composition root.
- D8 Each phase's full `pytest -n 8` runs on a worktree of its commit, in the background, while the next phase goes on.
- D9 `models/response.py` is split into `core/result/{result_code,operation_response,error_response}.py`; the
      duplicate `ErrorResponse` of `models/contacts.py` (finding 5) is deleted, star imports resolved to the other one.
- D10 `DomainTransferProcess` and `ContactTransferProcess` go to `core/model/shared`, because `message`'s
      `TransferEvent` holds them and the object packages import only `shared` (besides `domain → contact`).
- D11 `UnsupportedRppFeature` → `core/capabilities/UnsupportedFeature`: core does not name RPP.
- D12 `controller/helper/rpp_response.py` is split into `rpp/http/{headers,problem,context,operation}.py`;
      `handle_rpp_error` moves from `app.py` to `problem.py`, `get_backend` from `auth.py` to `context.py`.
      `requested_elements` goes to `rpp/handlers/shared/`, because it calls a mapper and `http` must not.
- D13 `SessionAuthenticator.authenticate` → `core/session/SessionPool.session`, which answers the backend; the token
      info `{"backend": …}` is made by `rpp/http/security/SessionSecurityHandler` (was `EppBasicSecurityHandler`), and
      `create_app(sessions, profile, …)`.
- D14 `rpp/handlers/__init__.py` re-exports the 41 handlers by name (checked: the same set as before), for
      `RelativeResolver('rpp.handlers')`. `rpp/dto/__init__.py` is empty.
- D15 `tests/unit/test_openapi_spec.py` had to change for the renames, so it is repaired in passing: #124 is fixed.
- D16 `rpp.http.app → rpp.mapping.domain.idn_tables` is an ignored import until phase 5 (finding 6).
- D17 Finding 6: `IdnTables` → `registry_adapter/epp/idn_tables.py`. `DomainIdn` holds the `lgr` instead of the table
      id. The EPP domain commands translate it with the tables `EppBackend` is given; the mapper refuses an LGR that is
      not in `BackendProfile.lgrs` (new), with the same 400. `epp_profile(idn_tables)` makes the EPP profile with
      them. The warning for a table without an LGR moves to the EPP parser.
- D18 Finding 7 (#17): `core/flows/read_back.py` and one `MutationResult` (`stored`) replace the three
      `_read_back`s and `*_mutation_result.py`. `create_domain` and `create_contact` are flows now. A contact create
      whose read-back fails answers 202, as domains and hosts already did (it was a 500).
- D19 Finding 8: `config.py` → `settings/` (`EppSettings`, `DiscoverySettings`, `Settings`, `load_settings`), loaded
      once by `main.py`, which passes each section on. The section fields keep the config.yaml key names. Handlers
      read the app configuration only through `rpp/http/context.py`.
- D20 `NotSupportedByProxy` takes the backend name in `detail()`, as `NotSupportedByBackend` does, so core does not
      name EPP; the answer is the same.
- D21 Phase 6: `OperationResponse[T]` carries `payload: T` (None for a command that carries nothing). The 22 `*Response`
      classes are gone; checks carry `core/model/shared/Availability(name, available, reason)`, poll and ack
      `core/model/message/MessageQueue(queue_size, message)`. `ErrorResponse` and `MessageErrorResponse` stay as they
      are. `ReplacementSteps.object_of` is gone: a read's object is its payload.
- D22 Follow-ups filed: #128 (EPP still named in `rpp/mapping` and `core` messages), #129 (EPP commands grouped by
      object, not by operation, D4).
