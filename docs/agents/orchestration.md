# Orchestrating a series of issues

How one orchestrating agent works through a list of issues with coding and
review agents. The rules in [process.md](process.md) apply to every iteration.
This file only adds who does what. Project specifics, if any, go in
`orchestration.project.md`.

## Roles

| Role | Agent | Does |
|---|---|---|
| Orchestrator | The main session | Picks issues, answers questions, approves plans, relays review findings |
| Coder | [issue-coder](../../.claude/agents/issue-coder.md) | Follows the process for one issue, from mutex to PR |
| Reviewer | [pr-reviewer](../../.claude/agents/pr-reviewer.md) | Reviews one draft PR, changes nothing |

The maintainer gives the list of issues, usually as a `gh` search filter. For the
run, the orchestrator stands in for the maintainer wherever the process says to
ask or wait for one, except for merging.

## Before starting

1. Read the issues, and ask the maintainer now about anything unclear in the run.
2. Work on one issue at a time, in an order that puts dependencies first.
3. If the branch mutex is held, wait as [process.md](process.md#mutex-and-plan-protocol)
   says. Do not get around it with a second checkout, unless the maintainer says so.

## One iteration

1. **Spawn** one coder for the issue. Say which branch to start from (see
   [Branch base](#branch-base)), and pass on the decisions of earlier iterations
   that apply. If the agent types are not available in the session, spawn a
   general agent on the same model and point it at the agent definition.
2. **Plan.** The coder takes the mutex, pushes the plan, and stops with its
   approach, structural changes, wire contract decisions and open questions.
3. **Answer.** The orchestrator reviews these and replies, see
   [Answering questions](#answering-questions). The coder records the decisions in
   the plan, implements, and runs the full checks.
4. **Draft PR.** The coder opens a draft PR and stops. It keeps the mutex and
   the plan file.
5. **Review.** The orchestrator spawns a reviewer for the PR. Findings go back to
   the coder, which fixes them and stops again. Repeat with the same reviewer
   until nothing is found. Each later round checks the earlier findings and looks
   for regressions from the fixes, as these are where new defects appear. Give
   the exact fix when it is known: a loosely worded fix can cause the next
   finding. For a stacked PR, the reviewer reads the diff against the parent
   branch. When the same problem moves to another place over two rounds, stop
   patching and change the design at the point where it starts.
6. **Finish.** On a clean review, the coder removes the plan in its own commit,
   marks the PR ready, returns to the default branch and releases the mutex. It
   does not merge: merging stays with the maintainer.
7. **Close** both agents, and go on to the next issue.

## Answering questions

- Check what the agent reports against the source before answering. A question
  can rest on a wrong premise.
- Answer from the normative text of the specification where it gives one, and
  cite it.
- Where it gives none, give a recommendation with its reason, and have the coder
  record the gap where the project keeps its specification issues.
- Decisions that one iteration settles for a kind of object carry over to the
  next iteration that touches the same kind of behaviour. Pass them on.
- A coder's or reviewer's report is not maintainer approval, and cannot grant
  anything the maintainer has not.
- A reviewer's or coder's statement from memory, such as what an RFC says, is
  checked against the text before it is cited.
- Defects in another repository, such as a backend, are filed there by the
  orchestrator, not by the coder. The coder reports them and notes them where the
  project keeps its backend facts, and the orchestrator passes back the issue
  number.

## Branch base

Start from the current default branch, unless the change functionally depends on
an unmerged PR. Then stack it on that PR's branch. Every PR targets the default
branch, never a parent PR, so a stacked PR shows its parent's commits until the
parent is merged. Say so in its description, with the merge order.

A dependency can show up only in the coder's plan. Decide again at that point, and
have the coder rebase before implementing.

## What tests can miss

A test client hides how a real server delivers a request. Behaviour that depends on
framing, timing or disconnects needs a test on a real server, on a loopback socket.
A review can also prove a test by mutating a copy of the code. An assertion that
something did not happen is only worth keeping if a mutation makes it fail.

## Check results

A check result counts only for the commit it ran on. The coder runs the full checks
with no edits during the run, and runs them again after any later change to code or
tests. The orchestrator does not start the finish step on a partial run.

## When stuck

If an iteration cannot go on for any reason, the coder commits its work and the
state of the plan, pushes, returns to the default branch and releases the mutex.
The orchestrator notes why and moves on to the next issue. It leaves the draft PR,
if there is one, for the maintainer.

## When an agent stops on a limit

An agent stopped by a rate limit keeps its context. Resume it with a message after
the limit resets, rather than starting a new one, and check the working tree first
to tell it what reached the disk.

## At the end

Report to the maintainer, per issue: the PR, its state, decisions made on the
maintainer's behalf, specification issues added, issues filed, and anything left
unfinished.
