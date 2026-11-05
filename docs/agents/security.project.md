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
  ([tcpclient.py:77](../../src/eppclient/tcpclient.py#L77)), including the login
  XML with `<pw>`. Received EPP messages are printed too. (#14)
- **Unescaped XML:** `_send_login` interpolates the username and password into the
  login XML ([eppclient.py:143](../../src/eppclient/eppclient.py#L143)). (#9)
- **Raw exception text in 500 responses:** `rpp_operation` passes `detail=str(e)` in
  [rpp_response.py](../../src/controller/helper/rpp_response.py). (#15)
