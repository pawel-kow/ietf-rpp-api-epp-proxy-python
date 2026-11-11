# Plan: run the tests in parallel

Branch `chore/parallel-tests`, requested by the maintainer on 2026-11-11 after a trial on `feature/35-restore-process`.

## Tasks

- [~] Add `pytest-xdist` to `requirements.txt`
- [ ] Document `pytest -n 8` as the check (testing.project.md, process.project.md), with the backend limit
- [ ] Full run with `pytest -n 8`, PR

## Findings (trial on feature/35-restore-process, 4-core devcontainer)

| Run | Workers | Wall | Result |
|---|---|---|---|
| Full suite | 4 | 9:09 | 2027 passed |
| Full suite | 8 | 8:09 | 2027 passed |
| Unit | 4 | 3:52 (10:45 CPU) | 1729 passed |
| Integration | 8 | 4:32 (0:22 CPU) | 298 passed |
| Integration | 16 | 2:49 | 89 failed: logins refused (pawel-kow/EPP-server-docker#7) |

- Names do not collide: `{random_name}` and `{random_id_10}` are made per worker at import, `{unique_cltrid}` per command.
- Unit tests are CPU-bound (#112), integration tests wait on the backend.

## Decisions

- `-n 8`: the most the backend takes; more gives nothing on 4 cores for the unit tests.

## Open questions

- None.
