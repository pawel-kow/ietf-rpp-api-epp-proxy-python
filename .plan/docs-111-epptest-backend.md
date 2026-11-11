# Plan: describe the current EPP test backend (#111)

Branch `docs/111-epptest-backend`, from `main`.

## Tasks

- [~] T1 `config.yaml` defaults to the compose service name `epp-server`, which resolves on the backend's network
      whatever the compose project is called
- [ ] T2 `docs/agents/testing.project.md`: backend as a compose project (`epptest`), network `<project>_epp_net`,
      attached by hand until #111 is fixed
- [ ] T3 Update #111 to the current setup
- [ ] T4 Integration run; PR

## Findings

- The backend now runs as compose project `epptest`; its server has the aliases `epptest-epp-server-1` and
  `epp-server` on `epptest_epp_net` (`docker inspect`). `epp-server-docker-epp-server-1` no longer exists.
- `postStartCommand` attaches no network since #109.

## Decisions

- The maintainer asked to update #111 and the doc to the new setup. The fix of `postStartCommand` stays in #111.
