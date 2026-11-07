# Messages (#37)

Base: `origin/feature/contact-transfer-34` (PR #90, stacked, merges first). Other open PRs #81, #83, #86, #88 are not needed.

## Tasks

- [x] Settle the open questions with the maintainer
- [x] Failing tests: EPP poll XML, poll/ack parsers, message mapper, wire cases, integration cases
- [x] models, eppclient, epp_to_model_mapper, rpp_to_model_mapper, flow, controller
- [x] `.spec/spec-issues.md`, `docs/agents/*.project.md`
- [~] Full `pytest`, draft PR
- [ ] `git rm` this plan, release the mutex on `main`

## Findings

- Today all four operations answer 501 `02101` through the missing-controller path, and the detail leaks `module 'controller' has no attribute ...` (read in the code, reproduced with the test client).
- Core §16.10.1 "EPP Compatibility Profile": always the oldest message, repeated GETs return the same message until acked, `type` is ignored, messages stay `queued`.
- Core §6.2: `RPP-Queue-Size` is a MAY, in any response. The OpenAPI lists it as optional on the message responses. No `RPP-Msgq-*` headers exist in core.
- Core §16.10.2: DELETE acks, no content in the response, Problem Detail on failure. Core §16.1.4: DELETE MUST reject content.
- Table 10: `01300` and `01301` are `x1yzz`, so 200. Neither is in Table 9. Core §18 IANA table lists both.
- json §6.8.3 / OpenAPI: the query response is an array of `message.read`.
- Backend probe (foo has hundreds of queued transfer messages, baz is empty): `req` gives `1301` with `msgQ count id`, `qDate`, `msg lang`, `domain:trnData` (pending, with `exDate`). `req` on an empty queue gives `1300`. `ack` with an unknown or non-numeric id gives `2303`.

## Plan

EPP mapping:

| RPP | EPP | Answer |
|---|---|---|
| `GET /messages` | `poll op="req"` | `1301`: 200, array with the one message. `1300`: 200, `[]` |
| `GET /messages/{id}` | `poll op="req"` | id equals the head: 200 message. Empty queue: 404 `02303`. Other id: 501 `02102` |
| `DELETE /messages/{id}` | `poll op="ack" msgID=id` | `1000`: 200, no content. Unknown id (EPP `2303`): 404 |
| `POST /messages` | none (server-only operation) | 501 `02101`, explicit handler |

`RPP-Queue-Size` from `msgQ/@count` on all responses of these operations. EPP message `msg/@lang` becomes `Content-Language`.

EPP to RPP message: `msgQ/@id` to `id`, `qDate` to `creationDate`, `status` is `queued`.

| EPP resData | RPP data |
|---|---|
| `domain:trnData`, `trStatus` pending | `transferRequestMessage` (`objectType` domainName, `objectId`, `status`, `requestDate`, `actionDate`, `process` as in the transfer endpoints) |
| `domain:trnData`, any other status | `transferOutcomeMessage` (`trStatus`, dates, `expiryDate`, `process`) |
| `contact:trnData` | the same two with `objectType` contact |
| `domain:panData`, `contact:panData`, `host:panData` | `reviewResponseMessage` (`approved` from `paResult`, `clientTransactionId`, `serverTransactionId`, `completionDate` from `paDate`, `message` from `msg`) |
| none, unknown, more than one element, or a response `extension` | `serviceNoticeMessage` with the `msg` text, plus a sentence naming what was not translated |

Modules (one class per file): `models/queue_message.py`, `transfer_event.py`, `pending_action_event.py`, `poll_response.py`, `ack_response.py`; `epp_to_model_mapper/commands/messages.py` and `messages.py`; `eppclient/epp_messages.py`; `rpp_to_model_mapper/messages.py` with `rpp_models/rpp_message*.py`; `flows/messages.py` (read by id is poll plus compare); `controller/messages.py`.

## Decisions

- Stack on #90. Rebased, own branch force-pushed with `--force-with-lease`.
- Empty queue: 200, `[]`, `01300`. Non-head id on read: 501 `02102`. Both in spec-issues.
- Anything that cannot become a valid typed message, including a failed `.read` validation, is a `serviceNoticeMessage`, never a 500. `qName` is logged without content.
- `process` is included, with no `processId`. `Content-Language` from `msg/@lang`, omitted if absent.
- `includeElements` not fixed: #95. Read-then-ack integration case: #96. `POST /messages` is an explicit 501 `02101`.
- Wire tests cover acking a real head.

## Open questions (answered, see Decisions)

1. Empty queue body: `[]` (query schema is an array). No normative text.
2. Read by id of a non-head id: 501 `02102`, as it cannot be told from an unknown id.
3. Unmappable message: service notice with a note, and the state logged. Transfer messages lose the `msg` text, as they have no member for it.
4. `process` in transfer messages: include, as `latest` is readable.
5. `includeElements` and `type` on `GET /messages`: `type` ignored by the profile; `includeElements` ignored as elsewhere.
6. DELETE needs the `require_empty_body` fix of #90 (stack on #90).
7. Integration cases cannot capture an id between steps, so the ack of a real head is covered by wire tests only.

## Review of a4dea20 (decisions)

- No message gives a 500: a reply the typed parser rejects is read with lxml and becomes a notice with the id, count, `qDate`, `msg` text and the qNames of `resData` and `extension` children. `fail_on_unknown_properties` stays strict. A bad `qDate` is dropped and the rest stays typed.
- An ack that succeeded at EPP is never an error. Unknown success codes count as `01000`; unknown error codes are `02400`.
- `1301` without a usable message id is a 500 (`02400`), the one exception (spec-issues).
- The `creationDate` substitute is the event date, else the read time, so it can differ between reads (spec-issues).
- `Content-Language` only when it is a language tag, `en` when `lang` is absent. `RPP-Queue-Size` only as an integer >= 0, also on the read 404 and 501 (`MessageErrorResponse`).
- Successful DELETE returns a Flask `Response` without `Content-Type`. HEAD handlers keep their `del`, cause noted on #87.
- Ids with control characters: 400 `02005` on GET and DELETE. A path that is `\r\n` alone never reaches the handler (framework-level 500, as for every route).
