# Plan: cors-expose-headers

The CORS and the profile error message fixes of #238, without its SIDN preset, which its author no longer needs.

## Tasks

- [~] CORS: `expose_headers` in `src/rpp/http/app.py`, with a unit test
- [ ] Profile error message for a `false` schema in `src/rpp/schema/schema_scope.py`, with a unit test
- [ ] Checks (lint-imports, unit tests, smoke)
- [ ] Draft PR, close #238 with a pointer to it

## Findings

- A browser client on another origin reads only the CORS-safelisted response headers. The proxy sends no
  `Access-Control-Expose-Headers`, so the client sees no `RPP-Cltrid`, `RPP-Svtrid` or `RPP-Code` (reproduced with the
  test client: a request with `Origin` gets `access-control-allow-origin` and no expose header).
- A `false` sub-schema of a profile (a member the profile does not allow) gives the reason
  "The value breaks the constraint 'None'": jsonschema has no validator name for it.

## Decisions

- Exposed: the headers the proxy sends that are not safelisted: `RPP-Cltrid`, `RPP-Svtrid`, `RPP-Code`,
  `RPP-Queue-Size`, `RPP-Preset` (header signalling) and `Location`. `RPP-Profile` and `Link` of #238 are left out: the
  proxy sends neither. `Content-Language` is safelisted. Draft issue: ietf-wg-rpp/draft-ietf-rpp-core#189.
