# Process

Project-agnostic workflow rules. Commands, labels and environment details are
in [process.project.md](process.project.md).

## General rules

1. **Always use the project's isolated environment** (virtualenv or equivalent),
   never the system interpreter or toolchain.
2. **Propose before restructuring.** Before any architecture, interface, or
   folder-structure change (new modules or packages, public API changes, new
   top-level directories, file reorganisation), propose the change and wait for
   explicit confirmation. Approval of a written plan counts as confirmation for
   the steps it defines.
3. **Verify with the project's own checks, not an approximation.** Before
   considering a change done, run every check the project documents, exactly as
   written. If the project has CI, run each CI step locally, in order.
   **Exception — docs-only changes:** a change touching only Markdown, `.plan/`,
   or comments in non-code files skips the test steps. Any change to code, tests,
   configs, fixtures, schemas or templates runs them in full.
4. **Behaviour changes are explicit.** Wire contracts (paths, field names, status
   and error codes, headers) are frozen. Changing one is a deliberate, documented
   decision with coordinated test updates, never a side effect.

## Mutex and plan protocol

1. **Branch mutex first.** If `.agent-sync.yml` exists, stop and poll every 15
   minutes. Otherwise create it atomically as a JSON file with `timestamp`,
   `branch` and `issue`. Never commit it. Remove it when finished and the
   checkout is back on `main`.
2. **Clean start.** `main` must be clean. If it is not, **stop and ask the
   maintainer** whether to stop, or to stash and pop at the end (a task in the
   plan). Then run `git pull --ff-only origin main`. Skip this if the maintainer
   asks to work on the current branch.
3. **Branch.** Every iteration has its own branch from `main`, with the exception
   in step 2.
4. **Plan.** Before changing anything, write `.plan/<branch>.md` (`/` becomes
   `-`) with tasks, findings with evidence, decisions, corrections and open
   questions. Commit and push it, keep it current, and keep exactly one task
   marked `[~]`.
5. **PR.** One per iteration, a draft until the checks pass and the maintainer
   has accepted it. Merging is done by hand.
6. **Before merge.** Defects found but not fixed become GitHub issues, and
   rationale goes in the commit message. Then `git rm` the plan file in its own
   commit.
7. **Release the branch mutex.**

## Issues

Open defects and follow-up work are GitHub issues, not markdown. `gh` must be
logged in (`gh auth login`).

When asked to file issues, open one per unfixed issue with `gh issue create`.
Keep them very concise, as a human developer would write them: the branch and
commit where it occurs, one or two lines on the problem, and a minimal
reproducer. Say so if something was only read in the code and not reproduced.
