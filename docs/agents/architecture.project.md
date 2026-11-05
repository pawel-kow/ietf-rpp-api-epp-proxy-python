# Architecture: project specifics

Generic rules are in [architecture.md](architecture.md).

## Request lifecycle

A request flows through distinct layers, each in its own package under `src/`. A
single feature (e.g. "domain update") touches every layer:

1. **`openapi.yaml`:** the API contract. Connexion routes operations to controller
   functions by `operationId` (e.g. `domainNames_updatePartial` →
   `controller.domains.domainNames_updatePartial`) via
   `RelativeResolver('controller')` in [src/app.py](../../src/app.py). An operation
   without a controller function answers 501 (`02101`). Generated, see below.
2. **`controller/`:** HTTP handlers. Parse the request, call the RPP→model mapper,
   call the eppclient and map the result back to RPP. EPP errors go through
   `raise_epp_error` in
   [rpp_response.py](../../src/controller/helper/rpp_response.py), which applies core
   §18.1, and `handle_rpp_error` in [src/app.py](../../src/app.py) renders every error
   as a core §9 Problem Detail.
3. **`rpp_to_model_mapper/`:** converts inbound RPP JSON dicts ↔ internal `models`
   dataclasses, through the RPP dataclasses in `rpp_models/`. Validates every payload
   against a JSON Schema via `validate_schema(...)` before mapping. Also does the
   reverse (`*_to_rpp`) and re-validates the outbound dict. Valid input the model
   cannot hold raises `UnsupportedRppFeature`, which answers 501 (`02102`), so nothing
   is dropped silently. `domain_patch.py` turns a JSON Patch into a `DomainUpdate`
   without reading the object, so operations that need the current state are
   unsupported (#27). `host_patch.py` does the same for a `HostUpdate`.
4. **`models/`:** the internal domain model (plain `@dataclass(kw_only=True)`),
   provider-neutral. `ResultCode` (an `Enum` of EPP codes with `(code, text)`
   tuples) and `OperationResponse`/`ErrorResponse` live in
   [src/models/response.py](../../src/models/response.py).
5. **`eppclient/`:** runs one EPP operation: build XML →
   `send_and_get_response` → parse. `epp_*` functions return a typed `*Response`
   model or an `ErrorResponse`, and controllers branch on `isinstance`.
   [eppclient.py](../../src/eppclient/eppclient.py) is the raw TCP+XML client
   (login/logout, `_parse_epp_response` reads the `<result code>`; codes matching
   `1xxx` = success).
6. **`flows/`:** multi-step operations, free of the web framework. A flow returns a
   typed result or an `ErrorResponse`, and the handler renders it. `flows/hosts.py`
   holds mutate-then-Info, and PUT as Info, difference, update and Info.
7. **`epp_to_model_mapper/`:** builds outbound EPP XML from models and parses
   inbound EPP XML into models. `epp_model/` holds xsdata-generated dataclasses for
   the EPP XSDs (domain-1.0, contact-1.0, secDNS-1.1, etc.). `commands/not_used/`
   is dead code: ignore it.

`domainNames_create`, `domainNames_updatePartial` and the host mutations do not build
their response from the create/update reply. They issue a **follow-up EPP Info** call and
map that to RPP, because EPP mutation responses don't echo full object state. If that Info fails, the
mutation has still been applied, so the handler answers **202** with no body and the
mutation's `RPP-*` headers. `openapi.yaml` does not define this 202 (#23 tracks the
question for the spec).

## Generated artifacts: do not hand-edit

`src/openapi.yaml` and `src/rpp_schema_validator/schemas/rpp.schema.normalized.json`
are copied verbatim from `.spec/auto/` by [copy_models.sh](../../copy_models.sh). The
JSON schema is the single source of truth for request/response validation. `$defs`
names (e.g. `"domainName.read"`) are passed by string to `validate_schema`. If
validation fails unexpectedly, check whether the schema and the mapper drifted.
A change to the contract goes to `.spec/auto/`, then through `copy_models.sh`. The
JSContact profile -02 changes there were made by hand and still have to reach
TypeSpec (#56). OpenAPI 3.0 cannot express all of them, so the JSON schema is the
stricter of the two.

Points in the drafts that cannot be implemented or are unclear go to
[.spec/spec-issues.md](../../.spec/spec-issues.md).

## Contact forms

A Card's internationalized form is the EPP `postalInfo type="int"` on `Contact`, and
its one localization is `postalInfo type="loc"` in `Contact.localizedPostalInfo`. What
the JSContact profile requires beyond the schema (key sequence, US-ASCII, key against
features) is checked in `rpp_to_model_mapper/contacts.py` on requests, before anything
the model cannot hold is rejected, so a profile violation is a 400 and not a 501.

## Wire contract

The frozen contract covers the OpenAPI paths and schemas, the core §18.1 result code
to HTTP status mapping, and the `RPP-*` headers. RPP result codes are EPP codes with a
leading `0`.

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
  `src/models/contacts.py` (7), `src/models/response.py` (3),
  `src/models/common.py` (3), `src/eppclient/tcpclient.py` (2).
  Generated `epp_model/` is exempt. (#20)
- **Flows in handlers:** the mutate-then-Info orchestration sits inside
  `domainNames_create`, `domainNames_updatePartial` and `contacts_create`. (#17)
