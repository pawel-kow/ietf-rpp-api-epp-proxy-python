# Security: project specifics

Generic rules are in [security.md](security.md).

## Invariants

- HTTP Basic credentials are passed straight through as the EPP `clID`/`pw`, or the RRI LOGIN `user`/`password`.
  They are the registrar's registry credentials, so treat them as high-value secrets. The RRI LOGIN is sent with
  `loggable=False`, so `TCPClient` does not print it. A CHPROV holds the domain's AuthInfo in plaintext and is sent
  with `loggable=False` too.
- RRI locks a user for an hour after 10 failed LOGINs, and every HTTP Basic attempt with a wrong password for a user
  without a session costs one: anyone who can reach the proxy can lock a RegAcc out. Accepted as a known risk for
  now (docs/rri/refactoring.md §7). The integration suite never sends a wrong password for a test account: its
  failed logins are of a user the backend does not know (`unknown_user` of the environment).
- RRI message texts and arguments can hold personal data: the adapter logs the codes of a reply's warnings and
  errors only, and a queue message shows its type and the names of the domains and handles it is about.
- The MTEST credentials are in `.env`, which is ignored by git; the runner reads it, the proxy never does.
- Every inbound and outbound RPP payload is validated with `validate_schema(...)`.
  See [architecture.project.md](architecture.project.md).

## Known debt

Read in the code, not reproduced.

- **Credentials in stdout:** `TCPClient` prints every sent message
  ([tcp_client.py:72](../../src/registry_adapter/common/transport/tcp_client.py#L72)), including the login
  XML with `<pw>`. Received EPP messages are printed too. (#14)
- **Unescaped XML:** `_send_login` interpolates the username and password into the
  login XML ([epp_client.py:175](../../src/registry_adapter/epp/session/epp_client.py#L175)). (#9)
- **Raw exception text in 500 responses:** `rpp_operation` passes `detail=str(e)` in
  [operation.py](../../src/rpp/http/operation.py). (#15)
