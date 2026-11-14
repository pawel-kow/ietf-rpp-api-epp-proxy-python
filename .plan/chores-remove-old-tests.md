# Plan: the integration cases as a tree, per backend

Branch `chores/remove-old-tests` (worked on as asked, not from `main`).

## Tasks

- [x] T1 Collect each `tests/integration/test_case_data/<group>/<case>.json` as its own pytest item
- [x] T2 Move the runner of `test_from_file_definition.py` to a module that is not collected (`file_cases.py`)
- [x] T3 `main.compose(settings)`: the app of any settings; `main:app` and its module names stay
- [x] T4 A tree per test environment (`file_cases.py` › environment › group › case), each with its own app,
      credentials and pacer; skips marked at collection
- [x] T5 Docs: `testing.project.md`, `process.project.md`, `architecture.project.md`
- [x] T6 `lint-imports`; the full `pytest -n 4` run (both environments): 2715 passed, 367 skipped, 38 min
- [x] T7 Smoke suite: `"markers": ["smoke"]` on 24 happy-path cases that run on both backends without a wait;
      `pytest -n 4 -m smoke` (48 tests) passed in 2 min 23 s. An unknown marker, or a smoke case a backend skips,
      fails that case

## Findings (evidence)

1. All 521 cases were params of `test_from_file_definition`, so VS Code listed them flat under the function.
2. The VS Code Python extension (`vscode_pytest/__init__.py`, `build_test_tree`) nests items only under
   `pytest.Class` chains and their file; folders come from paths. Its `build_test_tree`, run on this collection, gives
   `file_cases.py › epp-docker › contact_availability › test1-free`, without errors.
3. Three files have a `test_id` other than their stem (`contact_update/test5`, `test9`, `host_update/test15`).
4. A skipped `pytest.Item` needs a line number from `reportinfo`, or the report fails with an internal error.
5. VS Code runs a test by `<item.path>::<id after the file>`, so an item whose path is its JSON file is not found
   (`no match in any of [<Dir domain_create>]`) unless the JSON file collects that id. A case file named on the command
   line is therefore collected as a tree of that one case (`session.isinitpath`); a directory run does not collect
   it, so nothing runs twice. The item's path stays its JSON file, which the editor opens.

## Decisions

- Chosen by the maintainer: JSON files as tests; every environment runs in one session; cases a backend's selectors
  exclude are skipped at collection; an environment without credentials in `.env` is skipped with the variables it
  needs (option a).
- `RPP_TEST_ENV` is a comma-separated filter, unset means all; the unit tests compose the first it names.
- A run's workers are at most the smallest `max_workers` of the environments it tests: `-n 4` with MTEST.
- The item's name stays the case's `test_id`; `<group>-<test_id>` stays a `-k` keyword.
- The duplicate-id check goes: two files can no longer collapse into one node.
- Each case gets its own Flask test client (it was one per module).

## Open questions

None.
