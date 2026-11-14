# Plan: the integration cases as a tree of their data files

Branch `chores/remove-old-tests` (worked on as asked, not from `main`).

## Tasks

- [x] T1 Collect each `tests/integration/test_case_data/<group>/<case>.json` as its own pytest item (conftest
      collectors), so the test tree is folder → group → case file → case, not one flat parametrized function
- [x] T2 Move the runner of `test_from_file_definition.py` to a module that is not collected (`file_cases.py`)
- [x] T3 Docs: `testing.project.md` commands and test data format
- [~] T4 `lint-imports`; collection of every case (`--collect-only`); the integration run

## Findings (evidence)

1. All 521 cases are params of `test_from_file_definition`, so VS Code lists them flat under the function.
2. The installed VS Code Python extension (`vscode_pytest/__init__.py`, `build_test_tree`) nests a non-parametrized
   item under its `pytest.File` parent and the folders of its path.
3. Three files have a `test_id` other than their stem (`contact_update/test5`, `test9`, `host_update/test15`).

## Decisions

- Chosen by the maintainer: JSON files as tests (over one generated class per group).
- The item's name stays the case's `test_id`; `<group>-<test_id>` stays a `-k` keyword, so the documented
  `-k domain_lifecycle-test8` still selects it.
- A group directory is its own collector: it reads `_group.json` once and orders its files naturally (test2 before
  test10).
- The duplicate-id check goes: the node id is the file path, so two cases can no longer collapse into one.
- Each case gets its own Flask test client (it was one per module).

## Open questions

None.
