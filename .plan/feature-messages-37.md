# Messages (#37)

Base: `main` at 5258d2b. Open PRs #81, #83, #86, #88, #90 are not merged.

## Tasks

- [~] Settle the open questions with the maintainer
- [ ] Failing tests: EPP poll XML, poll/ack parsers, message mapper, wire cases, integration cases
- [ ] models, eppclient, epp_to_model_mapper, rpp_to_model_mapper, flow, controller
- [ ] `.spec/spec-issues.md`, `docs/agents/*.project.md`
- [ ] Full `pytest`, draft PR
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

(none yet)

## Open questions

1. Empty queue body: `[]` (query schema is an array). No normative text.
2. Read by id of a non-head id: 501 `02102`, as it cannot be told from an unknown id.
3. Unmappable message: service notice with a note, and the state logged. Transfer messages lose the `msg` text, as they have no member for it.
4. `process` in transfer messages: include, as `latest` is readable.
5. `includeElements` and `type` on `GET /messages`: `type` ignored by the profile; `includeElements` ignored as elsewhere.
6. DELETE needs the `require_empty_body` fix of #90 (stack on #90).
7. Integration cases cannot capture an id between steps, so the ack of a real head is covered by wire tests only.
