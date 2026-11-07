# Agent guide

Guidance for coding agents working in this repository. This file and the
`docs/agents/<area>.md` files are project-agnostic. Everything specific to this
project lives in `docs/agents/<area>.project.md`.

## Working agreement

- **Never assume — ask when in doubt.** If a requirement, expected behaviour, or
  the intent behind a change is ambiguous, stop and ask the user rather than
  guessing. A wrong assumption is expensive to unwind.
- **Present the solution for acceptance before implementing.** For any
  non-trivial change, describe the approach and wait for the user's go-ahead
  before editing code.
- **Track found issues as GitHub issues**, not in markdown. See
  [process.md](docs/agents/process.md#issues).
- **Every edit to these docs follows their structure.** Generic rules go in
  `<area>.md`, project specifics in `<area>.project.md`. If unsure which applies,
  ask the user. See [documentation.md](docs/agents/documentation.md).

## Documentation map

Each area has a generic `<area>.md` and, where needed, a `<area>.project.md`
with this project's specifics. Read both. If they conflict, ask the user.

**Before any task,** read [overview.project.md](docs/agents/overview.project.md),
[process.md](docs/agents/process.md) and
[process.project.md](docs/agents/process.project.md). Then read what the task
touches:

| Area | Read when | Generic | Project |
|---|---|---|---|
| Requirements | Specifying a feature nobody has specified yet | [requirements.md](docs/agents/requirements.md) | — |
| Architecture | Changing or adding code | [architecture.md](docs/agents/architecture.md) | [architecture.project.md](docs/agents/architecture.project.md) |
| Testing | Writing or running tests | [testing.md](docs/agents/testing.md) | [testing.project.md](docs/agents/testing.project.md) |
| Security | Touching input handling, credentials, logging or error output | [security.md](docs/agents/security.md) | [security.project.md](docs/agents/security.project.md) |
| Documentation | Changing these docs, or anything they describe | [documentation.md](docs/agents/documentation.md) | — |
| Orchestration | Working through a series of issues with coding and review agents | [orchestration.md](docs/agents/orchestration.md) | — |
