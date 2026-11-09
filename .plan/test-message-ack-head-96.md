# test/message-ack-head-96: integration case that reads the head of the queue and acks it (#96)

An integration case: a transfer request queues a message for the losing registrar (`foo`), `GET /messages`
reads the head, a step captures its `id`, `DELETE /messages/{id}` acks it with 200.

## Tasks

- [x] Runner: `field_value` reads a list element by index (`0.id`), so a step can capture from the list
      body of `GET /messages`. Unit tests first.
- [x] Case `message/test6-read_head_then_ack.json`.
- [x] `testing.project.md`: acking a real head is now an integration case.
- [x] `config.local.yaml` next to `config.yaml` replaces its top-level keys, and is gitignored (maintainer, 2026-11-09).
- [x] Runner: `{upper:TEXT}` placeholder (TEXT in upper case), for `match` values in the form the registry stores.
- [x] 24 domain cases create the contacts, hosts and domains they use, instead of the seeded `FO-TEST1`..`4`,
      `ns1`/`ns2`/`ns9.bar.example` and `NOT-FREE.EXAMPLE`. `domain_create/test7` creates the domain it then
      finds taken (409 `02302`). `ns9` stays uncreated: `domain_update/test10` needs a match that finds nothing.
- [~] Full `pytest` with the backend.

## Findings

- `field_value` (tests/helper/integration_api_test.py) walks dicts only: `"0" in [...]` is a membership test,
  so `capture: {"head": "0.id"}` fails with "Field '0.id' not found".
- Core §16.10.2: a successful ack is 200 without content, and the message is permanently removed. Its example
  carries `RPP-Code: 01000` and `RPP-Queue-Size`.
- The queue is shared per registrar and other cases add to it, so the case asserts the shape of the head only
  and acks whatever is at the head. After its own transfer request the queue is not empty, so the GET is
  `01301` and not `any_of`.
- The backend host `epp-server-docker-epp-server-1` does not resolve in this container (2026-11-09). The backend
  answers as `epp-server:743`, and only to pytest, which the maintainer excluded from the Bash sandbox. The runs
  here set `rpp_epp_host: epp-server` in an untracked `config.local.yaml`.
- The `epp-server` backend has none of the seeded objects: 24 cases fail on `2303` for `FO-TEST1` and
  `NS1.BAR.EXAMPLE`, and `domain_create/test7` creates `NOT-FREE.EXAMPLE` instead of a 409.
- The backend stores host names in upper case: `ns1.p1-<x>.net` reads back as `NS1.P1-<X>.NET` (probed).
  A `match` is exact, so it needs the upper-case form of a generated name.
- `domain_delete/test4` and `domain_update/test25` name seeded objects only in requests refused with 400 before
  EPP, so they stay. `tests/integration/test_domain_create.py` and `test_domain_delete.py` assign
  `test_cases = []` and discard their lists, so their seeded data never runs.

## Decisions

- Maintainer, 2026-11-09: cases create what they need, with data unique per case (testing.md), in this PR.
  Contacts are `FO-{random_id_10}` plus a suffix of the case, hosts are external `nsN.<case>-{random_name}.net`.
- A second `DELETE` of the same id answers 404 `02303`, which shows the message was removed (core §16.10.2).
  Confirmed against the backend: `message/test6` passes (2026-11-09).

## Open questions

- None.
