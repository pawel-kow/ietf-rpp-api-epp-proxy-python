# Security: project specifics

Generic rules are in [security.md](security.md).

## Invariants

- HTTP Basic credentials are passed straight through as the EPP `clID`/`pw`, or the RRI LOGIN `user`/`password`.
  They are the registrar's registry credentials, so treat them as high-value secrets. The RRI LOGIN is sent with
  `loggable=False`, so `TCPClient` does not print it. A CHPROV holds the domain's AuthInfo in plaintext and is sent
  with `loggable=False` too. So is every RRI exchange that can carry verification data (the extension's "MUST NOT log"): a contact CREATE/UPDATE with blocks, contact INFO and the recursive domain INFO of the verification process, and a command sent
  `loggable=False` has its reply not printed either (`unit/test_rri_verification_logging.py`).
- RRI locks a user for an hour after 10 failed LOGINs, and every HTTP Basic attempt with a wrong password for a user
  without a session costs one: anyone who can reach the proxy can lock a RegAcc out. Accepted as a known risk for
  now (docs/rri/refactoring.md §7). The integration suite never sends a wrong password for a test account: its
  failed logins are of a user the backend does not know (`unknown_user` of the environment).
- RRI message texts and arguments can hold personal data: the adapter logs the codes of a reply's warnings and
  errors only, and a queue message shows its type and the names of the domains and handles it is about.
- The SQLite demo backend holds the clients as `scrypt` hashes (`rpp_sqlite_clients`), compared with
  `hmac.compare_digest`, and a login of an unknown user costs the same as a known one's. A hash is a credential: it and
  the password are never logged. The demo passwords in `config/backends/sql.yaml` and `tests/integration/environments/sqlite-demo.yaml`
  are documented demo values and are never a deployment's. The authInfo of a planet is stored as given (a read shows it
  to its sponsor, as EPP does) and compared in constant time on a transfer request.
- The MTEST credentials are in `.env`, which is ignored by git; the runner reads it, the proxy never does.
- Every inbound and outbound RPP payload is validated with `validate_schema(...)`.
  See [architecture.project.md](architecture.project.md).

## Known debt

Read in the code, not reproduced.

- **Credentials in stdout:** `TCPClient` prints every sent message
  ([tcp_client.py:72](../../src/registry_adapter/common/transport/tcp_client.py#L72)), including the login
  XML with `<pw>`. Received messages are printed too, except the reply to a command sent `loggable=False` (the RRI exchanges that carry verification data or a secret). (#14)
- **Unescaped XML:** `_send_login` interpolates the username and password into the
  login XML ([epp_client.py:175](../../src/registry_adapter/epp/session/epp_client.py#L175)). (#9)
- **Raw exception text in 500 responses:** `rpp_operation` passes `detail=str(e)` in
  [operation.py](../../src/rpp/http/operation.py). (#15)
