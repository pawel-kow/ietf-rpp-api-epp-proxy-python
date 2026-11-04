# Architecture: project specifics

Generic rules are in [architecture.md](architecture.md).

## Request lifecycle

A request flows through distinct layers, each in its own package under `src/`. A
single feature (e.g. "domain update") touches every layer:

1. **`openapi.yaml`:** the API contract. Connexion routes operations to controller
   functions by `operationId` (e.g. `domains_Update` →
   `controller.domains.domains_Update`) via `RelativeResolver('controller')` in
   [src/run.py](../../src/run.py). Generated, see below.
2. **`controller/`:** HTTP handlers. Parse the request, call the RPP→model mapper,
   call the eppclient, map the result back to RPP, and translate EPP result codes
   into HTTP status plus `ProblemException`. See
   [RPP_IMPLEMENTATION_NOTES.md](../../RPP_IMPLEMENTATION_NOTES.md): 2302→409,
   2303→404, other client errors→400, server errors→500.
3. **`rpp_to_model_mapper/`:** converts inbound RPP JSON dicts ↔ internal `models`
   dataclasses. Validates every payload against a JSON Schema via
   `validate_schema(...)` before mapping. Also does the reverse (`*_to_rpp`) and
   re-validates the outbound dict.
4. **`models/`:** the internal domain model (plain `@dataclass(kw_only=True)`),
   provider-neutral. `ResultCode` (an `Enum` of EPP codes with `(code, text)`
   tuples) and `OperationResponse`/`ErrorResponse` live in
   [src/models/response.py](../../src/models/response.py).
5. **`eppclient/`:** orchestrates one EPP operation: build XML →
   `send_and_get_response` → parse. `epp_*` functions return a typed `*Response`
   model or an `ErrorResponse`, and controllers branch on `isinstance`.
   [eppclient.py](../../src/eppclient/eppclient.py) is the raw TCP+XML client
   (login/logout, `_parse_epp_response` reads the `<result code>`; codes matching
   `1xxx` = success).
6. **`epp_to_model_mapper/`:** builds outbound EPP XML from models and parses
   inbound EPP XML into models. `epp_model/` holds xsdata-generated dataclasses for
   the EPP XSDs (domain-1.0, contact-1.0, secDNS-1.1, etc.). `commands/not_used/`
   is dead code: ignore it.

`domains_Create` and `domains_Update` do not build their response from the
create/update reply. They issue a **follow-up EPP Info** call and map that to RPP,
because EPP mutation responses don't echo full object state.

## Generated artifacts: do not hand-edit

`src/openapi.yaml` and `src/rpp_schema_validator/schemas/*.json` are copied in from
a sibling **TypeSpec** project by [copy_models.sh](../../copy_models.sh) (expects
`../ietf-rpp-api-typespec/tsp-output/`). The JSON schemas are the single source of
truth for request/response validation. Schema names (e.g. `"Domain"`,
`"DomainUpdateModel"`) are passed by string to `validate_schema`. If validation
fails unexpectedly, check whether the schema and the mapper drifted: the fix
usually belongs in the TypeSpec project, not here.

## Wire contract

The frozen contract covers the OpenAPI paths and schemas, the EPP→HTTP status
mapping, and the `RPP-*` headers.

## Configuration

`Config` in [src/config.py](../../src/config.py) loads `config.yaml` at import time
(path overridable via `RPP_CONFIG_FILE`). `rpp_epp_connection_cache` (default
`false`) toggles between stateless per-request EPP connections and a cached,
stateful connection. The EPP backend host and port come from `rpp_epp_host` and
`rpp_epp_port`, and `new_epp_client` in [src/run.py](../../src/run.py) uses them to
open the connection.

## Composition

[src/run.py](../../src/run.py) is the composition root: it builds the default
`EPPClient` factory and passes it to
[`EppSessionAuthenticator`](../../src/controller/epp_session_authenticator.py), which
goes to `create_app` in [src/app.py](../../src/app.py). `create_app` hands
`authenticate` to Connexion through `security_map`, because Connexion would otherwise
resolve the function by name and it could not receive dependencies.

## Known debt

Do not copy these patterns (see [architecture.md](architecture.md#known-debt)).

- **Several classes per file:** `src/models/domains.py` (18),
  `src/models/contacts.py` (8), `src/models/response.py` (3),
  `src/models/common.py` (3), `src/eppclient/tcpclient.py` (2),
  `src/rpp_to_model_mapper/rpp_models/rpp_domains.py` (17),
  `src/rpp_to_model_mapper/rpp_models/rpp_contact.py` (4),
  `src/rpp_to_model_mapper/rpp_models/rpp_common.py` (2). Generated `epp_model/`
  is exempt. (#20)
- **Flows in handlers:** the mutate-then-Info orchestration sits inside
  `domains_Create` and `domains_Update`. (#17)
- **Error mapping repeated per handler:** each function in `src/controller/`
  hand-writes its own EPP-code→HTTP branches, which is how `domains_Update` once
  missed 2303→404. Not all branches pass the RPP headers (e.g. `domains_Get`).
  (#16)
