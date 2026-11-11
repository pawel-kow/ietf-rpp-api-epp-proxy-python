# Plan: backend capabilities behind an injected BackendProfile (#117)

Branch `refactor/117-backend-profile`, stacked on `refactor/116-backend-port` (#118), re-targeted to `main` once #118
is merged. Phase 2 of `docs/rri/refactoring.md` (on `feature/denicrri`) §6, §3.7 and §3.10.

## Tasks

- [~] T1 `registry/backend_profile.py`: `BackendProfile` with every fact of §3.7; `eppclient/epp_profile.py`:
      `EPP_PROFILE` with today's values; `RegistryBackend.profile`
- [ ] T2 `NotSupportedByEpp(feature)` → `NotSupportedByBackend(feature)`; `map_request` names the backend from the
      injected profile, so the EPP text stays `… cannot be expressed in EPP`. `epp_refusal.py` uses the same wording
- [ ] T3 Injection: `run.py` → `create_app(authenticator, profile, …)` → `app.config["RPP_BACKEND_PROFILE"]` →
      handlers → the domain mappers, which check `contact_labels` and `domain_record_types` from the profile
- [ ] T4 Discovery takes `objects` and `profiles` from the profile
- [ ] T5 Tests: profile, a domain mapper and discovery with a profile that differs from EPP; existing tests pass
      `EPP_PROFILE`
- [ ] T6 Docs: `architecture.project.md` (unsupported input, configuration, composition, discovery), `testing.project.md`
- [ ] T7 Full `pytest -n 8` green; draft PR

## Findings (evidence)

1. `NotSupportedByEpp` is raised at about 30 places in 12 mapper modules (`rpp_to_model_mapper/`), and its text
   names EPP. Unit and wire tests assert `cannot be expressed in EPP`.
2. The facts the mappers check today: `domains.CONTACT_LABELS` (`check_contact_label`, used by `domains`,
   `domain_patch` and `domain_wanted`) and `domain_dns.ZONE_APEX_RECORDS`. The address records are glue in both.
3. `controller/discovery.py` has `OBJECTS` and `PROFILES` as constants.
4. `map_request` is called outside an app in some unit tests.

## Decisions

- D1 (maintainer) Stack on #118.
- D2 (maintainer) Mappers raise `NotSupportedByBackend(feature)`, and `map_request` adds the name of the injected
  profile. Only mappers that check a capability take the profile.
- D3 (maintainer) Every field of §3.7 now, with EPP values. Fields that nothing checks yet (`max_registrants`,
  `host_objects`, `client_statuses`, `contact_fax`, `contact_localization`, `contact_region`, `contact_phones_max`,
  `supports_renew`, `supports_contact_delete`, `supports_transfer_query`) are read by the RRI phases.
- D4 The profile is required where it is taken (`create_app`, the domain mappers), keyword-only in the mappers, so
  a caller cannot forget it and fall back to EPP's facts silently.
- D5 `EPP_PROFILE` lives in the EPP adapter (`eppclient/epp_profile.py`); `registry/` holds only the type.
- D6 `contact_phones_max` counts the voice numbers: EPP holds one (`voice`), a fax is `contact_fax`.

## Open questions

None.
