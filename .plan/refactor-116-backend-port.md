# Plan: backend port between the flows and EPP (#116)

Branch `refactor/116-backend-port`, from `main` at `a63b339`.
Status: phase 1 of `docs/rri/refactoring.md` (on `feature/denicrri`) §6. The maintainer accepted the layout of §3 and
§4 as written, phases 1–2 only, branches from `main`.

## Tasks

- [x] T1 `registry/` port: `RegistryBackend`, `DomainGateway`, `ContactGateway`, `HostGateway`, `MessageGateway`
      (`typing.Protocol`, one per file), imports `models` only
- [x] T2 Move `derived_update.py`, `ReplaceOutcome`, `ReplacementSteps` from `flows/` to `registry/`, without `EPPClient`
- [x] T3 EPP adapter in `eppclient/`: `EppBackend` and one gateway per object; the EPP replacement steps and the EPP
      refusals (`epp_refusal.py`, `epp_contact_refusal.py`) move there from `flows/`
- [x] T4 Flows take a `RegistryBackend`; `require_sponsor` compares with `backend.sponsor_id`
- [x] T5 Controllers call `get_backend()`; `raise_epp_error` → `raise_registry_error`; `TransferHandlers` takes the
      gateway of its object
- [x] T6 `EppSessionAuthenticator` → `SessionAuthenticator`, token key `backend`; `run.py` builds `EppBackend`
- [x] T7 Tests follow the renames; unit tests of `EppBackend` and of `derived_update` without EPP
- [x] T8 Docs: `architecture.project.md` (lifecycle, composition), `testing.project.md` (test doubles)
- [~] T9 Full `pytest -n 8` green; draft PR

## Findings (evidence)

1. Flows and controllers call `epp_*` functions with an `EPPClient` (`flows/*.py`, `controller/{domains,contacts,
   hosts,messages,transfer_handlers,domain_transfers,contact_transfers}.py`).
2. `flows/derived_update.py` takes `epp_client` only to pass it to `steps.read` and `steps.update`.
3. `flows/sponsor.py:require_sponsor` reads `epp_client.username`.
4. `read_domain_restore` uses `epp_domains_RestoreInfo`, an Info that first checks the RGP extension. §3.1 lists no
   such method.
5. `flows/contacts.py:_lost_form` and `flows/hosts.py:_replaced` read the delta that was sent
   (`ReplaceOutcome.update`).

## Decisions

- D1 The gateway method signatures are those of today's `epp_*` functions without the client: `info(name,
  client_transaction_id=None)`. §3.1's `info(name, auth_info=None)` is not added, nothing passes one today.
- D2 `DomainGateway.restore_info` is added for finding 4. Its name is RGP's "restore", so RRI can answer it.
- D3 One class per file: the EPP adapter is `eppclient/epp_backend.py` plus `epp_domain_gateway.py`,
  `epp_contact_gateway.py`, `epp_host_gateway.py`, `epp_message_gateway.py`.
- D4 The session is the backend: the factory of `SessionAuthenticator` returns a `RegistryBackend`, which has
  `connect`, `connected`, `verify_credentials` and `disconnect`. `EppBackend` delegates them to its `EPPClient`.
- D5 `ReplaceOutcome.update` stays the delta that was sent (finding 5), the EPP adapter fills it. It is `None` when
  nothing changed.

## Results

- `pytest -n 8`: 2110 passed, 5 skipped (8 min), unit and EPP integration (`epptest`).

## Open questions

None.
