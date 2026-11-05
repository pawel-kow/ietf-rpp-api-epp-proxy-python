# TLS connection to the EPP server (#63, with #11)

## Tasks

- [x] Failing tests: TLS context, TCPClient wrapping, loopback TLS server, short reads
- [x] `eppclient/tls.py`, `TCPClient` TLS and `_recv_exact`, `Config`, `run.py`
- [x] `config.yaml`: port 743, TLS on, `rpp_epp_tls_insecure_skip_verify: true`
- [x] Docs: `architecture.project.md`, `testing.project.md`, `security.project.md`
- [x] Full `pytest`: 657 passed, 19 skipped
- [~] Draft PR, maintainer acceptance

## Findings

- Backend 743: default context fails with `CERTIFICATE_VERIFY_FAILED`; without
  verification TLS 1.2, greeting received.
- `SSLSocket.send(b'')` returns 0, so the liveness check in `TCPClient.send` stays.
- `src/config.yaml` is a symlink to `config.yaml`.

## Decisions (maintainer)

- Opt-in is the boolean `rpp_epp_tls_insecure_skip_verify`, default false. It turns off
  both the certificate and the hostname check.
- #11 is fixed here, because a reply over 16 KB is cut short over TLS.
- No key in the repository: the test certificate is generated per session with `openssl`.
- `rpp_epp_timeout` stays out of scope, #8 stays open for it and `connection_cache`.

## Open questions

None.
