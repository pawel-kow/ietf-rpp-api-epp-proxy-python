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
   reverse and re-validates the outbound dict. Every module converts one thing through
   `rpp_to_model` and `model_to_rpp`, so the module name selects the conversion, and
   callers write `rpp_mapper.domains.rpp_to_model`. Valid input that cannot reach the
   backend answers 501, so nothing is dropped silently, see
   [Unsupported input](#unsupported-input). The one exception is the self-referencing `ns` record of a
   host, which EPP represents implicitly: it is mandatory on input and goes no further, see
   [spec-issues.md](../../.spec/spec-issues.md#the-own-ns-record-of-a-host). `dns_records.py` holds what hosts and domains share for DNS
   records, and `domain_dns.py` maps a domain's `dns` to `hostAttr` and secDNS.
   A mapper returns the intent it got, and never a mix: a partial update is a delta (`DomainUpdate`,
   `ContactUpdate`, `HostUpdate`), a full update is the wanted state (`DomainReplacement`,
   `ContactReplacement`, `HostReplacement`). `domain_patch.py` turns a JSON Patch into a `DomainUpdate`
   without reading the object, and answers `None` when an operation needs the current state (whole-array
   `replace` or `remove`, `replace` with `match`, a partial `match`, `/status`, `/dns`, `/dns/records`,
   `/dns/controls`). `rpp_to_model_with_current` then applies the patch to the read representation of the domain
   with `json_patch.py` (json §5.2.2), and `domain_wanted.py` turns the patched representation into the
   `DomainReplacement`. A patch that matches no element, or matches several for a `replace`, is
   `PatchNotApplicable` (`02308`, 422). `host_patch.py` and `contact_patch.py` do the same for hosts and contacts.
   `domain_replacement.py`, `contact_replacement.py` and `host_replacement.py` turn a PUT into the replacement
   without a read: they reject members outside the `.update` schema, and what the body omits is cleared. An
   `onDemand` data element (`authInfo`) is part of a PUT only when the request includes it, see
   [spec-issues.md](../../.spec/spec-issues.md#visibility-and-includeelements).
   `contacts.py` also holds `contact_from_rpp`, the Card conversion that create, PUT and PATCH share.
   `contact_patch.py` sends `/status`, `/authInfo`, and an `add` or `replace` of a phone or the email without a
   read, and reads for the rest of `/contactInfo`, see
   [spec-issues.md](../../.spec/spec-issues.md#full-update-of-a-contact).
   `include_elements.py` checks the `includeElements` of a request against the data model and hides an `onDemand`
   element the request does not include, for every object, from the Visibility in
   `rpp_schema_validator/schemas/draft-ietf-rpp-data-objects.yaml`.
   `idn_tables.py` holds `IdnTables`, the map between a domain's `lgr` and the table of the EPP IDN extension, which
   `domains.rpp_to_model` and `domains.model_to_rpp` take from the handler. `domain_availability.rpp_to_model` refuses
   the `uName` and `lgr` parameters of a check, see [spec-issues.md](../../.spec/spec-issues.md#idn).
   `patch_statuses.py` hides server statuses from a patch, on hosts, domains and contacts, see
   [spec-issues.md](../../.spec/spec-issues.md#status-in-json-patch).
   `rpp_authorization.py` converts the `RPP-Authorization` header to an `AuthInfo`, and
   `domain_transfer_process.py` and `domain_transfer_reject.py` convert a domain transfer,
   `contact_transfer_process.py` and `contact_transfer_reject.py` a contact transfer, and
   `domain_renew_process.py` a renewal. `domain_restore_process.py` converts a restore request and renders a restore,
   `domain_restore_report.py` a report (PUT) and `domain_restore_patch.py` a report sent as a JSON Patch (PATCH).
   `date_time.py` checks an RFC 3339 date-time.
4. **`models/`:** the internal domain model (plain `@dataclass(kw_only=True)`),
   provider-neutral. Next to the classes it holds the pure conversions between the two kinds of update, written
   once per object: `<object>_difference.difference(current, wanted)` gives the delta that turns the stored
   object into the replacement, and `<object>_application.apply(current, delta)` the replacement a delta amounts
   to (unused by EPP, for a backend that updates by replacement). A replacement's `unchanged` names the members
   it does not state, which stay as stored: the data elements with onDemand Visibility the request did not include
   (`stated_members.stated` fills them in from the stored object). Nothing in this is specific to `authInfo`. `contact_localization.as_stored` puts a wanted
   contact in the terms of the stored one, because a read shows a localization by its differences from the card. `ResultCode` (an `Enum` of EPP codes with `(code, text)`
   tuples) and `OperationResponse`/`ErrorResponse` live in
   [src/models/response.py](../../src/models/response.py).
5. **`eppclient/`:** runs one EPP operation: build XML →
   `send_and_get_response` → parse. `epp_*` functions return a typed `*Response`
   model or an `ErrorResponse`, and controllers branch on `isinstance`.
   [eppclient.py](../../src/eppclient/eppclient.py) is the raw TCP+XML client
   (login/logout, `_parse_epp_response` reads the `<result code>`; codes matching
   `1xxx` = success). It keeps the extensions of the greeting for
   `supports_extension`, and logs in with those of `LOGIN_EXTENSIONS` (secDNS, IDN and RGP) the server offers. Before a command it asks the transport whether the server has closed the idle
   session (`closed_by_peer`) and logs in again if so. A failed send is sent once more on a new session, a failed
   receive never, because the server may have run the command.
6. **`flows/`:** multi-step operations, free of the web framework. A flow returns a
   typed result or an `ErrorResponse`, and the handler renders it. `patch_<object>` and `replace_<object>` in
   `flows/domains.py`, `flows/contacts.py` and `flows/hosts.py` take a delta (`update`) or a replacement. A delta
   is sent as it is, then the object is read back. EPP has no full update, so a replacement goes through
   `derived_update.replace`, the one derivation for every object: it reads the object (unless a PATCH has read it
   already), lets the object's `ReplacementSteps` prepare the wanted state and refuse what EPP cannot clear
   (`epp_contact_refusal.py`, as an `ErrorResponse`), sends the `difference` as one update, and answers a
   `ReplaceOutcome`. When nothing changes it sends nothing and the outcome is `unchanged`. `flows/sponsor.py`
   then holds the 403 for a client that is not the sponsor, which sends no EPP command to say so. The read and the
   update are not atomic.
7. **`epp_to_model_mapper/`:** builds outbound EPP XML from models and parses
   inbound EPP XML into models. `epp_model/` holds xsdata-generated dataclasses for
   the EPP XSDs (domain-1.0, contact-1.0, secDNS-1.1, etc.). `commands/not_used/`
   is dead code: ignore it.

`domainNames_create`, `domainNames_updatePartial`, `domainNames_update` and the host mutations do not build
their response from the create/update reply. They issue a **follow-up EPP Info** call and
map that to RPP, because EPP mutation responses don't echo full object state. If that Info fails, the
mutation has still been applied, so the handler answers **202** with no body and the
mutation's `RPP-*` headers. `openapi.yaml` does not define this 202 (#23 tracks the
question for the spec).

Transfer handlers are in `controller/domain_transfers.py` and `controller/contact_transfers.py`, thin
functions over `TransferHandlers` in `controller/transfer_handlers.py`. An EPP `<transfer>` reply carries
the state of the transfer, so they need no follow-up Info. `epp_domains_Transfer` and
`epp_contacts_Transfer` run all five operations, chosen by the model's `operation`. EPP has no process ids, so only
`latest` is implemented, see [spec-issues.md](../../.spec/spec-issues.md#transfer-process).

Messages are in `controller/messages.py`. `GET /messages` is EPP `poll req`, `DELETE /messages/{id}` is
`poll ack`, and `GET /messages/{id}` is `poll req` followed by a comparison of ids in `flows/messages.py`,
because EPP cannot read past the head. `str_to_epp` and `decode_xml` read EPP replies without entities or a DTD, and a DOCTYPE is refused. `epp_to_model_mapper/messages.py` turns the reply into a `QueueMessage`
whose `event` is a `TransferEvent` (domain and contact `trnData`) or a `PendingActionEvent` (`panData`), and
`rpp_to_model_mapper/messages.py` renders it. Anything the proxy cannot translate, or that fails the `.read`
schema, or a reply that does not follow the EPP schema, becomes a `serviceNoticeMessage` that names the elements
(never their content), so a client can always read and acknowledge it. The one exception is a `1301` without a
message id or an unreadable result, which is a 500. A code the proxy has no name for is an `UnknownResultCode`, which answers by Table 10. `Content-Language` is the `lang` of the `msg` (`en` when absent), see
[spec-issues.md](../../.spec/spec-issues.md#messages).

`BodyBufferingMiddleware` in `controller/body_buffering_middleware.py` is the middleware that `create_app`
adds after security and before Connexion's validators, so an anonymous client gets its 401 before its body is read. It reads the whole body of a request that has one before anything else runs, drops the request if the client
disconnects first, and passes on a complete request with a `content-length`. So chunked bodies, late bodies and
aborted uploads reach no handler half-received. It has no size limit (#93).

The restore handlers are `domainNameRestoreProcesses_create`, `_update`, `_updatePartial` and `_read` in
`controller/domains.py`. A request and a report are a domain update with the RFC 3915 `rgp:restore` extension, sent by
`epp_domains_Restore`, and answer 200 without `Location`. `read_domain_restore` in `flows/domains.py` reads the domain
and answers 404 when its RGP statuses show no restore under way. Only domains have a restore, see
[spec-issues.md](../../.spec/spec-issues.md#restore-process).

The renew handler is `domainNameRenewProcesses_renewCreate` in `controller/domains.py`, and `renew_domain` in
`flows/domains.py` runs it. EPP needs `curExpDate`, so a request without `expiryDate` first has the domain read.
The EPP renew reply carries the new expiry date, so there is no read-back, and the answer is a 200 without
`Location`, see [spec-issues.md](../../.spec/spec-issues.md#renew-process).

`RppRequestBodyValidator` and `RppResponseBodyValidator` let a body be absent where the
OpenAPI allows it, which Connexion's validators do not. The handler then gets an empty dict.

## Generated artifacts: do not hand-edit

`src/openapi.yaml` and `src/rpp_schema_validator/schemas/rpp.schema.normalized.json`
are copied verbatim from `.spec/auto/` by [copy_models.sh](../../copy_models.sh), and
`src/rpp_schema_validator/schemas/draft-ietf-rpp-data-objects.yaml` from `.spec/`. The
JSON schema is the single source of truth for request/response validation, the data model for the Visibility of
the data elements (`visibility_of`). `$defs`
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

## Unsupported input

Valid input that cannot reach the backend answers 501. There are three kinds, each with
its own message:

| Kind | Raised as | RPP code |
|---|---|---|
| EPP has no place for it, in the core or in an extension the proxy knows of | `NotSupportedByEpp` | `02102` |
| EPP can hold it, but the proxy does not map it | `NotSupportedByProxy` | `02103` if it names an extension, otherwise `02102` |
| The proxy uses an extension the server does not offer | `ErrorResponse` from `epp_*` | `02103` |

An extension the proxy does not know of cannot be told apart from no extension, so it
counts as the first kind. A PATCH that EPP could do once the proxy has read the object
is the second kind.

The third kind is known only from the EPP greeting, which mappers cannot reach, so the
`epp_*` function checks `supports_extension` and `raise_epp_error` renders the result.

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
open the connection. `rpp_idn_lgr_tables` maps an LGR name to an IDN table id, one to one. `run.py` turns it into
`IdnTables`, which refuses a map that is not one to one, so the app does not start with one. Without it no `lgr` is
accepted. `rpp_epp_use_tls` (default `true`) connects over TLS with the
certificate and hostname verified. `rpp_epp_tls_insecure_skip_verify` (default `false`)
turns both checks off, for test backends only.

`rpp_base_url`, `rpp_tlds`, `rpp_environment_name` and `rpp_environment_status` are what the
discovery document (`GET /.well-known/rpp`, no authentication, no EPP) states. `controller/discovery.py`
adds the RPP version and the supported objects, which are constants. Without all four, it answers
500 (`02400`) and logs the keys, never the values. A setting is also missing when it has the wrong shape: `rpp_base_url` must be an absolute `https` URL, `rpp_tlds` a non-empty list of non-empty strings. `profiles` is the constant `epp-compatibility`, though `GET /profiles/{name}` is 501. The base URL is never taken from the request. The proxy does not
check the `version` parameter of the media type, so core §12's 406 is not enforced (#41). See
[spec-issues.md](../../.spec/spec-issues.md#discovery).

## Composition

[src/run.py](../../src/run.py) is the composition root: it builds the default
`EPPClient` factory and passes it to
[`EppSessionAuthenticator`](../../src/controller/epp_session_authenticator.py), which
goes to `create_app` in [src/app.py](../../src/app.py), with `config` as the settings of the discovery document, which the handler reads from the app configuration, and the `IdnTables`, which the domain handlers read from it the same way. `create_app` hands
`authenticate` to Connexion through `security_map`, because Connexion would otherwise
resolve the function by name and it could not receive dependencies.

## Known debt

Do not copy these patterns (see [architecture.md](architecture.md#known-debt)).

- **Several classes per file:** `src/models/domains.py` (17),
  `src/models/contacts.py` (7), `src/models/response.py` (3),
  `src/models/common.py` (3), `src/eppclient/tcpclient.py` (2).
  Generated `epp_model/` is exempt. (#20)
- **Flows in handlers:** the mutate-then-Info orchestration sits inside
  `domainNames_create`, `domainNames_updatePartial` and `contacts_create`. (#17)
