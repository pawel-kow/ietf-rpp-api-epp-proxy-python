# Security: project specifics

Generic rules are in [security.md](security.md).

## Invariants

- HTTP Basic credentials are passed straight through as the EPP `clID`/`pw`. They
  are the registrar's registry credentials, so treat them as high-value secrets.
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
