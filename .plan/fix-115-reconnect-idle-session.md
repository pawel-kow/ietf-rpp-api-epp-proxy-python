# fix/115-reconnect-idle-session

Issue #115: a session the backend closed after idling gives a 500.

## Tasks

- [x] `TCPClient.closed_by_peer()`: an idle socket that is readable (EOF, TLS close_notify, unasked reply) is closed. Drop the `send(b'')` probe in `send`.
- [x] `EPPClient.send_and_get_response`: log in again before sending when the session was closed; on a failed send, log in again and send once more; never retry after the command was sent. Raise when no session can be opened (also `supports_extension`).
- [x] Fake transports get `closed_by_peer`.
- [x] Unit tests `tests/unit/test_eppclient_reconnect.py` with a loopback server that closes the session.
- [~] Run `pytest -n 8`, and the serial `pytest` once (`message/test1-query_head`).
- [x] Docs: architecture.project.md (eppclient).

## Findings

- Read only: after a failed send, `_send_and_get_response` disconnects and clears `_connected`, so only the first request after the close fails, not every later one.
- `send(b'')` on an SSL socket does not detect a peer close.
- When `connect()` fails, `send_and_get_response` went on sending on a socket without greeting or login.

## Decisions

- Accepted by the maintainer: check before sending, retry once after a failed send, never after the command was sent (a create or transfer may have run).
