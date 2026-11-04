# Constructor injection for EPP dependencies (#18, #19)

Maintainer asked to work on the current branch, no new branch for now.

## Tasks

- [x] Failing tests with stubs
- [x] `EPPClient(transport, username, password)` (#19)
- [x] `EppSessionAuthenticator(client_factory)` replaces `basic_auth` and `CLIENTS` (#18)
- [x] `EppBasicSecurityHandler(authenticate)` passed to Connexion through `security_map`
- [x] `create_app(authenticator)` in `app.py`, `run.py` becomes the composition root
- [x] Update `architecture.project.md` and `testing.project.md`
- [x] Full `pytest` with the live backend: 61 passed, 2 skipped

## Findings

- Connexion resolves `BASICINFO_FUNC` by name and calls it with `(username, password)`,
  so a function cannot receive dependencies. `security_map` replaces the handler instead.
- `SecurityHandlerFactory` calls `security_handler()` with no arguments, so the map
  value has to be a zero-argument callable.
- `main` is 22 commits behind and does not contain the code the issues describe.
- Baseline before changes: 47 passed, 2 skipped.

## Decisions

- Constructor injection throughout. A module-level setter was proposed and rejected
  by the maintainer.
- No wire behaviour changes. Session caching and locking logic moves unchanged.

## Open questions

None.
