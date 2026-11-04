# Formulating new features

When asked to specify or implement a feature that is **not yet specified** (no
plan step, spec section or document defines it), do not start designing or
coding. Act as a requirements engineer and interview the user until the
requirements are agreed.

## Interview rules

- **Ask why and what, never how.** Explore the problem, motivation, affected
  users, expected behaviour and boundaries. Do not discuss implementation until
  the requirements are confirmed.
- **Consult project documentation, not source code.** Use the docs to understand
  current behaviour and to avoid asking what is already documented. Do not read
  the source during this phase.
- **Interview in small rounds.** A few focused questions at a time, building on
  previous answers. Reflect back what you understood before moving on.
- **Surface conflicts.** When a requirement contradicts documented behaviour, a
  frozen wire contract, a security invariant or another requirement, point it out
  and let the user decide.

## Topics to cover

1. **Why:** the problem or opportunity, who has it, what happens today, and how
   success is recognised.
2. **What:** expected behaviour from the user's or client's point of view,
   including the affected surfaces.
3. **Scope:** what is explicitly in and out.
4. **Edge cases and failures:** what the user sees when things go wrong.
5. **Constraints:** security, privacy and compatibility expectations that are
   requirements rather than design choices.

## Acceptance criteria

- Write them from the project owner's perspective: observable behaviour, each one
  testable and unambiguous (*Given … when … then …*), free of implementation
  detail.
- Present the complete summary (why, what, scope, out of scope, acceptance
  criteria, open questions) and get the user's **explicit confirmation**. Iterate
  until confirmed.
- **The confirmed user story lands as a GitHub issue** (`gh issue create`). The
  body contains the user story (*As a … I want … so that …*), the why, scope and
  out of scope, the acceptance criteria as a checklist, and open questions. Show
  the title and body in the summary: confirming the summary authorises creating
  the issue. Report the URL. Later design, plans, commits and PRs reference it.
- Design and implementation start only after confirmation, following
  [process.md](process.md) and [testing.md](testing.md). The acceptance criteria
  are the basis for the failing tests.
