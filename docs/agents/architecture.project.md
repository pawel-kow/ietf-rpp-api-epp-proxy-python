# Architecture: project specifics

Generic rules are in [architecture.md](architecture.md).

## Module boundaries

`src/` holds a protocol-free core, the RPP adapter that receives requests, and the registry adapters, each split by
registry object (#120). The rules below are checked by `import-linter`.

### Structure

```
src/
├── main.py                  composition root, the only module that knows all others
├── settings/                loads config.yaml once into typed sections, which main.py passes on
│   └── profiles/            epp.yaml, rri.yaml: the generic backend profile of each protocol
├── core/                    pure Python: no I/O, no framework, no protocol
│   ├── model/{shared,domain,contact,host,message}/
│   ├── result/              ResultCode, UnknownResultCode, OperationResponse, ErrorResponse
│   ├── capabilities/        BackendProfile, NotSupportedByBackend, NotSupportedByProxy
│   ├── ports/               RegistryBackend, *Gateway, ReplaceOutcome, ReplacementSteps, derived_update
│   ├── session/             SessionPool
│   └── flows/               read_back.py, mutation_result.py, sponsor.py, {domain,contact,host,message}/
├── rpp/                     receiving adapter: RPP over HTTP
│   ├── http/                app (create_app), middleware/, validators/, security/, problem, headers, context, operation
│   ├── handlers/            {domain,contact,host,message}/, shared/, discovery.py
│   ├── mapping/             shared/, {domain,contact,host,message,discovery}/
│   ├── dto/                 the RPP dataclasses
│   ├── schema/              validator, data_objects, schemas/ (generated)
│   └── openapi.yaml         (generated)
└── registry_adapter/
    ├── epp/
    │   ├── session/         EPPClient: greeting, login, extensions
    │   ├── xml/             codec (ns_map passed in), generated/
    │   ├── commands/        {domain,contact,host,message}/<operation>.py, shared/
    │   ├── gateways/        EppBackend, Epp*Gateway
    │   ├── idn_tables.py    lgr <-> EPP IDN table
    │   └── refusals.py, contact_refusal.py
    ├── rri/
    │   ├── session/         RriClient: LOGIN (no greeting), LOGOUT, lock, re-login, RegAccId of the login
    │   ├── xml/             codec, generated/ (xsdata, from docs/rri/xsd by generate_rri_models.sh)
    │   ├── commands/        {domain,contact,message}/<operation>.py, shared/rri_command.py (run, CTID)
    │   ├── gateways/        RriBackend, Rri*Gateway (hosts: every command UNIMPLEMENTED)
    │   ├── result_codes.py  DENIC code → ResultCode
    │   └── statuses.py      RRI domain status → RPP status
    └── common/
        ├── session/         SerialSession: lock, re-login, retry rule
        ├── transport/       TCP client, TLS context
        └── xmlsafe/         hardened parser, decode_xml
```

`registry_adapter/common` holds only protocol-agnostic infrastructure. The full update derived from partial ones, and
the partial one derived from a full one, are domain logic and stay in `core/ports`. The session behaviour both
protocols share, `common/session/serial_session.py` (`SerialSession`: the lock, re-login on a closed session, resend
only of a command never written), is the base of `EPPClient` and `RriClient`, which add their login and logout
([rule 6](architecture.md#same-pattern-for-the-same-thing)).

Package `__init__.py` files are empty, except `rpp/handlers/__init__.py`, which names every handler for Connexion
(see [Request lifecycle](#request-lifecycle)). Imports are absolute and name the module that defines what they import.

### Dependency rules

- `core` imports only the standard library.
- `rpp` imports `core` only, never `registry_adapter`.
- `registry_adapter/<protocol>` imports `core` and `registry_adapter/common`, never another protocol and never `rpp`.
- `registry_adapter/common` imports no project package: no `core`, no protocol, no `settings`.
- Only `main` imports more than one adapter. Nobody but `main` imports `settings`.
- Inside `core`: `flows → ports → model, result, capabilities`. The object sub-packages of `model` import only
  `model/shared`, except `domain → contact` for contact references.
- Inside `rpp`: `handlers → mapping, http`; `mapping → dto, schema`. `mapping` never imports `http`, Flask or
  Connexion.
- Inside `epp`: `gateways → commands → xml, session`; `session → common/transport`. Only `session` sends.
- Inside `rri`: `gateways → commands → session → xml`; the session logs in and reads replies in XML. Only `session`
  sends. `epp` and `rri` never import each other.

### What each module must never know

| Module | Must never know |
|---|---|
| `core.model` | HTTP, JSON, RPP field names, JSON Patch, schemas, XML, EPP/RRI names, sockets, config |
| `core.result` | HTTP status codes, `RPP-*` headers, Problem Details |
| `core.capabilities` | Which backend it is, beyond the profile's `name` |
| `core.ports` / `core.flows` | Any concrete backend, wire format, HTTP, RPP representations, `includeElements` |
| `rpp.mapping` | HTTP objects, EPP/RRI, IDN table ids, the session, the gateways |
| `rpp.handlers` | XML, the backend protocol, orchestration (that belongs in flows) |
| `rpp.http` | Object semantics, the backend protocol |
| `registry_adapter.*` | HTTP, RPP JSON, OpenAPI, Problem Details, `includeElements`, config files |
| `registry_adapter.common` | Which protocol uses it, the model, the result codes |

### The check

`import-linter` checks the rules, one contract per rule, configured in `[tool.importlinter]` of
[pyproject.toml](../../pyproject.toml) and run with `PYTHONPATH=src lint-imports` (see
[process.project.md](process.project.md#checks-before-done)). A forbidden contract also follows indirect imports.
`main.py` is a module, which import-linter cannot take as a root, so an import of `main` is forbidden by name and what
`main` imports is not checked. `protocols-independent` keeps `epp` and `rri` apart. Every
`ignore_imports` entry is known debt below; never add one for new code. The "must never know" table is not checked
by imports where it is about names and messages; see the known debt.

## Request lifecycle

A request flows through the layers below. A single feature (e.g. "domain update") touches a handler, a mapper, a
flow, the port and the EPP commands of one object.

1. **`rpp/openapi.yaml`:** the API contract. Connexion routes an operation by its `operationId` (e.g.
   `domainNames_updatePartial`) to the function of that name in `rpp.handlers`, via `RelativeResolver('rpp.handlers')`
   in [app.py](../../src/rpp/http/app.py). [rpp/handlers/\_\_init\_\_.py](../../src/rpp/handlers/__init__.py) names
   every handler for it. An operation without a handler answers 501 (`02101`). Generated, see below.
2. **`rpp/handlers/<object>/`:** the handlers, thin presenters. They parse the request, call the mapper, call a flow
   or the request's backend (`get_backend()` in [context.py](../../src/rpp/http/context.py)) and map the result
   back to RPP. `requested_elements` and `TransferHandlers` are in `rpp/handlers/shared/`.
3. **`rpp/http/`:** what every handler shares. `operation.py` holds `rpp_operation` (anything unexpected is a 500
   Problem Detail) and `map_request`, which runs a mapper and turns what it refuses into a Problem Detail.
   `problem.py` applies core §18.1 to registry errors (`raise_registry_error`) and renders every error as a core §9
   Problem Detail (`handle_rpp_error`). `headers.py` builds the `RPP-*` headers. `context.py` is the only reader of
   the app configuration and the request context: the backend, the `BackendProfile` and the discovery settings.
4. **`rpp/mapping/`:** converts inbound RPP JSON dicts ↔ the `core.model` dataclasses, through the RPP dataclasses in
   `rpp/dto/`. Validates every payload against a JSON Schema via `validate_schema(...)` (`rpp/schema/validator.py`)
   before mapping. Also does the
   reverse and re-validates the outbound dict. Every module converts one thing through
   `rpp_to_model` and `model_to_rpp`, so the module name selects the conversion, and
   handlers write `domain_patch.rpp_to_model`. Valid input that cannot reach the
   backend answers 501, so nothing is dropped silently, see
   [Unsupported input](#unsupported-input). The one exception is the self-referencing `ns` record of a
   host, which EPP represents implicitly: it is mandatory on input and goes no further, see
   [spec-issues.md](../../.spec/spec-issues.md#the-own-ns-record-of-a-host). `shared/dns_records.py` holds what hosts
   and domains share for DNS records, and `domain/domain_dns.py` maps a domain's `dns` to `hostAttr` and secDNS.
   A mapper returns the intent it got, and never a mix: a partial update is a delta (`DomainUpdate`,
   `ContactUpdate`, `HostUpdate`), a full update is the wanted state (`DomainReplacement`,
   `ContactReplacement`, `HostReplacement`). `domain_patch.py` turns a JSON Patch into a `DomainUpdate`
   without reading the object, and answers `None` when an operation needs the current state (whole-array
   `replace` or `remove`, `replace` with `match`, a partial `match`, `/status`, `/dns`, `/dns/records`,
   `/dns/controls`). `rpp_to_model_with_current` then applies the patch to the read representation of the domain
   with `shared/json_patch.py` (json §5.2.2), and `domain_wanted.py` turns the patched representation into the
   `DomainReplacement`. A patch that matches no element, or matches several for a `replace`, is
   `PatchNotApplicable` (`02308`, 422). `host_patch.py` and `contact_patch.py` do the same for hosts and contacts.
   `domain_replacement.py`, `contact_replacement.py` and `host_replacement.py` turn a PUT into the replacement
   without a read: they reject members outside the `.update` schema, and what the body omits is cleared. An
   `onDemand` data element (`authInfo`) is part of a PUT only when the request includes it, see
   [spec-issues.md](../../.spec/spec-issues.md#visibility-and-includeelements).
   `contact/contacts.py` also holds `contact_from_rpp`, the Card conversion that create, PUT and PATCH share.
   `contact_patch.py` sends `/status`, `/authInfo`, and an `add` or `replace` of a phone or the email without a
   read, and reads for the rest of `/contactInfo`, see
   [spec-issues.md](../../.spec/spec-issues.md#full-update-of-a-contact).
   `shared/include_elements.py` checks the `includeElements` of a request against the data model and hides an
   `onDemand` element the request does not include, for every object, from the Visibility in
   `rpp/schema/schemas/draft-ietf-rpp-data-objects.yaml`.
   A domain's `lgr` must be one of `BackendProfile.lgrs`, the LGRs the backend offers; `domain_availability.rpp_to_model`
   refuses the `uName` and `lgr` parameters of a check, see [spec-issues.md](../../.spec/spec-issues.md#idn).
   `shared/patch_statuses.py` hides server statuses from a patch, on hosts, domains and contacts, see
   [spec-issues.md](../../.spec/spec-issues.md#status-in-json-patch).
   `shared/rpp_authorization.py` converts the `RPP-Authorization` header to an `AuthInfo`, and
   `domain_transfer_process.py` and `domain_transfer_reject.py` convert a domain transfer,
   `contact_transfer_process.py` and `contact_transfer_reject.py` a contact transfer, and
   `domain_renew_process.py` a renewal. `domain_restore_process.py` converts a restore request and renders a restore,
   `domain_restore_report.py` a report (PUT) and `domain_restore_patch.py` a report sent as a JSON Patch (PATCH).
   `shared/date_time.py` checks an RFC 3339 date-time.
5. **`core/model/`:** the internal domain model (plain `@dataclass(kw_only=True)`),
   provider-neutral. Next to the classes it holds the pure conversions between the two kinds of update, written
   once per object: `<object>_difference.difference(current, wanted)` gives the delta that turns the stored
   object into the replacement, and `<object>_application.apply(current, delta)` the replacement a delta amounts
   to (unused by EPP, for a backend that updates by replacement). A replacement's `unchanged` names the members
   it does not state, which stay as stored: the data elements with onDemand Visibility the request did not include
   (`shared/stated_members.stated` fills them in from the stored object). Nothing in this is specific to `authInfo`.
   `contact/contact_localization.as_stored` puts a wanted contact in the terms of the stored one, because a read
   shows a localization by its differences from the card. A domain's IDN is its `lgr` and `uname` (`DomainIdn`).
6. **`core/result/`:** the answer of the registry. `OperationResponse` carries the `ResultCode` (an `Enum` of EPP
   codes with `(code, text)` tuples), the message and the transaction ids, and as its `payload` what the command
   carries back: the object of a read or create, the `Availability` of a check, the process of a transfer, renewal or
   restore, the `MessageQueue` of a poll or ack, and None for a delete or update. `ErrorResponse` is a refusal, and
   `MessageErrorResponse` (in `core/model/message`) one that knows the size of the queue. A code the proxy has no name
   for is an `UnknownResultCode`.
7. **`core/ports/`:** the backend port. `RegistryBackend` is one user's session with
   the registry: `domains`, `contacts`, `hosts` and `messages` are its gateways (`DomainGateway` …, each a
   `typing.Protocol`), `sponsor_id` is the id the registry stores as sponsor, and `profile` the `BackendProfile`. A
   gateway method returns an `OperationResponse` or an `ErrorResponse`, and callers branch on `isinstance`.
   `update(delta)` is a partial update and
   `replace(wanted, current=None)` a full one, which answers a `ReplaceOutcome`. `derived_update.replace` derives a
   full update from a partial one, once for every object and backend: it reads the object (unless the caller has
   read it), lets the object's `ReplacementSteps` prepare the wanted state and refuse what the backend cannot clear,
   sends the `difference` as one update, and answers the `ReplaceOutcome`. When nothing changes it sends nothing and
   the outcome is `unchanged`. The read and the update are not atomic.
8. **`core/flows/`:** multi-step operations over a `RegistryBackend`, free of the web framework and of the protocol. A
   flow returns a typed result or an `ErrorResponse`, and the handler renders it. `create_<object>`, `patch_<object>`
   and `replace_<object>` in `core/flows/<object>/<object>_flows.py` create, take a delta (`update`) or a
   replacement, and call the gateway's `create`, `update` or `replace`, then read the object back with `read_back`,
   once for every object. A PATCH that needs the current state passes the read it made as `current`. When the
   outcome is `unchanged`, `sponsor.py` holds the 403 for a client that is not the sponsor (`backend.sponsor_id`),
   which sends no command to say so.
9. **`registry_adapter/epp/`:** the EPP adapter. `EppBackend` in `gateways/` is the `RegistryBackend` over one
   `EPPClient`, whose login is the sponsor id, with the namespace map the commands render with and the `IdnTables`.
   `EppDomainGateway`, `EppContactGateway`, `EppHostGateway` and `EppMessageGateway` call the `epp_*` functions of
   `commands/<object>/<operation>.py` (`commands/domain/create.py`, `commands/message/poll.py` …). EPP has no full update, so each `replace` goes through
   `derived_update.replace`, with the refusal of what RFC 5733 cannot clear on a contact (`contact_refusal.py`).
   An operation's module holds all of it: the xsdata request (`domain_create`), its XML (`create_domain_xml`), the
   parser of the reply and the `epp_*` function that runs it: build XML → `send_and_get_response` → parse. What
   several operations of an object share is in its `common.py` (the create reply is parsed as an info reply, so
   `create.py` imports `parse_domain_response` from `info.py`). `commands/shared/` reads the result and transaction
   ids of a reply. [epp_client.py](../../src/registry_adapter/epp/session/epp_client.py) is the raw TCP+XML client
   (login/logout, `_parse_epp_response` reads the `<result code>`; codes matching
   `1xxx` = success). It keeps the extensions of the greeting for
   `supports_extension`, and logs in with those of `LOGIN_EXTENSIONS` (secDNS, IDN and RGP) the server offers. Before
   a command it asks the transport whether the server has closed the idle
   session (`closed_by_peer`) and logs in again if so. A failed send is sent once more on a new session, a failed
   receive never, because the server may have run the command. `xml/codec.py` renders a request with the namespace
   map it is given and parses a reply; `xml/generated/` holds xsdata-generated dataclasses for the EPP XSDs
   (domain-1.0, contact-1.0, secDNS-1.1, etc.). `idn_tables.py` maps a domain's `lgr` to the table of the EPP IDN
   extension and back, for the domain commands.
10. **`registry_adapter/common/`:** `transport/tcp_client.py` and `transport/tls.py` carry the bytes, and
    `xmlsafe/xml_helper.py` reads XML without entities or a DTD. `TCPClient` takes the `framing`: the length prefix
    counts itself (`LENGTH_INCLUDES_HEADER`, RFC 5734, the default) or the payload only (`LENGTH_OF_PAYLOAD`, RRI),
    and `send(message, loggable=False)` does not print a message that holds a credential.
11. **`registry_adapter/rri/`:** the DENIC RRI 5.0 adapter, XML only (gap Q20). `RriBackend` is the
    `RegistryBackend` over one `RriClient`; its `sponsor_id` is the RegAccId of the login, so one deployment serves
    several RegAccs. `commands/shared/rri_command.run` sends one request and turns the reply into an
    `OperationResponse` or an `ErrorResponse` with the DENIC code as `registry_code` (`result_codes.py`; a code whose
    meaning depends on the command is mapped by the command), logs the codes of warnings and errors only, and gives
    a write its CTID: the client's `RPP-Cltrid`, `-n` added for the n-th write of one request, or a UUID when the id
    is no RRI token. RRI updates by replacement only, so `RriDomainGateway.replace` and `RriContactGateway.replace`
    are native (UPDATE, or CHHOLDER when the holders change, then DELETE-/CREATE-AUTHINFO1; a contact UPDATE sends
    the verification data it read again, from `Contact.carried_over`), and `update(delta)` is derived through
    `derived_update.update`, which reads, applies the delta with `<object>_application.apply` and replaces. A
    domain's further holders are contacts labelled `registrant`, General Request and Abuse are `generalRequest` and
    `abuse`, and `a`/`aaaa`/`mx` entries are `ZoneRecord`s. An IDN is sent with its U-label as `handle` and its
    A-label as `ace`. A domain in its redemption period has no sponsor in INFO and reads with the sponsor `unknown`
    (spec-issues.md, "Sponsor of a deleted domain"). A request whose second command fails answers a
    `PartiallyApplied` (core/result) with the first command's transaction ids and the refusal, which `read_back` does
    not read back, so the handler answers 202 (gap Q7). The adapter refuses only what an RRI
    request has no place for, which RRI would never see: a person's name on an organisation's contact (an ORG is
    named by its organisation), a contact authInfo, a `uName` that is not the name, an AuthInfo1 RRI does not take
    (RRI receives only its hash), and a domain without DNS data (CREATE and UPDATE hold at least one `dnsentry`).
    Everything else is sent, and RRI's refusal answered by its code: changing a contact's name, clearing a member it
    requires. An `lgr` is
    not sent. A contact create sends the kind of the Card (PERSON or ORG, a PERSON may name its organisation); an
    update keeps the type RRI holds. Hosts, transfers, renew and contact delete answer `UNIMPLEMENTED_COMMAND`. Every queue
    message is a service notice naming its RRI type and the domains and handles it is about, with 1301 or 1300 as a
    poll has.

`domainNames_create`, `domainNames_updatePartial`, `domainNames_update`, `contacts_create`, the contact updates and
the host mutations do not build
their response from the create/update reply. Their flow issues a **follow-up EPP Info** call, `read_back`, and the
handler maps that to RPP, because EPP mutation responses don't echo full object state. If that Info fails, the
mutation has still been applied, so the handler answers **202** with no body and the
mutation's `RPP-*` headers. `openapi.yaml` does not define this 202 (#23 tracks the
question for the spec).

Transfer handlers are in `rpp/handlers/domain/domain_transfer_handlers.py` and
`rpp/handlers/contact/contact_transfer_handlers.py`, thin
functions over `TransferHandlers` in `rpp/handlers/shared/transfer_handlers.py`. An EPP `<transfer>` reply carries
the state of the transfer, so they need no follow-up Info. `epp_domains_Transfer` and
`epp_contacts_Transfer` run all five operations, chosen by the model's `operation`. EPP has no process ids, so only
`latest` is implemented, see [spec-issues.md](../../.spec/spec-issues.md#transfer-process).

Messages are in `rpp/handlers/message/message_handlers.py`. `GET /messages` is EPP `poll req`,
`DELETE /messages/{id}` is `poll ack`, and `GET /messages/{id}` is `poll req` followed by a comparison of ids in
`core/flows/message/message_flows.py`,
because EPP cannot read past the head. `str_to_epp` and `decode_xml` read EPP replies without entities or a DTD, and
a DOCTYPE is refused. `commands/message/poll.py` turns the reply into a `QueueMessage`
whose `event` is a `TransferEvent` (domain and contact `trnData`) or a `PendingActionEvent` (`panData`), and
`rpp/mapping/message/messages.py` renders it. Anything the proxy cannot translate, or that fails the `.read`
schema, or a reply that does not follow the EPP schema, becomes a `serviceNoticeMessage` that names the elements
(never their content), so a client can always read and acknowledge it. The one exception is a `1301` without a
message id or an unreadable result, which is a 500. A code the proxy has no name for is an `UnknownResultCode`, which
answers by Table 10. `Content-Language` is the `lang` of the `msg` (`en` when absent), see
[spec-issues.md](../../.spec/spec-issues.md#messages).

`BodyBufferingMiddleware` in `rpp/http/middleware/` is the middleware that `create_app`
adds after security and before Connexion's validators, so an anonymous client gets its 401 before its body is read.
It reads the whole body of a request that has one before anything else runs, drops the request if the client
disconnects first, and passes on a complete request with a `content-length`. So chunked bodies, late bodies and
aborted uploads reach no handler half-received. It has no size limit (#93).

The restore handlers are `domainNameRestoreProcesses_create`, `_update`, `_updatePartial` and `_read` in
`rpp/handlers/domain/domain_handlers.py`. A request and a report are a domain update with the RFC 3915 `rgp:restore`
extension, sent by `epp_domains_Restore`, and answer 200 without `Location`. `read_domain_restore` in
`core/flows/domain/domain_flows.py` reads the domain
and answers 404 when its RGP statuses show no restore under way. Only domains have a restore, see
[spec-issues.md](../../.spec/spec-issues.md#restore-process).

The renew handler is `domainNameRenewProcesses_renewCreate` in `rpp/handlers/domain/domain_handlers.py`, and
`renew_domain` in `core/flows/domain/domain_flows.py` runs it. EPP needs `curExpDate`, so a request without
`expiryDate` first has the domain read.
The EPP renew reply carries the new expiry date, so there is no read-back, and the answer is a 200 without
`Location`, see [spec-issues.md](../../.spec/spec-issues.md#renew-process).

`RppRequestBodyValidator` and `RppResponseBodyValidator` in `rpp/http/validators/` let a body be absent where the
OpenAPI allows it, which Connexion's validators do not. The handler then gets an empty dict.

## Generated artifacts: do not hand-edit

`src/rpp/openapi.yaml` and `src/rpp/schema/schemas/rpp.schema.normalized.json`
are copied verbatim from `.spec/auto/` by [copy_models.sh](../../copy_models.sh), and
`src/rpp/schema/schemas/draft-ietf-rpp-data-objects.yaml` from `.spec/`. The
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
features) is checked in `rpp/mapping/contact/contacts.py` on requests, before anything
the model cannot hold is rejected, so a profile violation is a 400 and not a 501.

## Unsupported input

Valid input that cannot reach the backend answers 501. There are three kinds, each with
its own message:

| Kind | Raised as | RPP code |
|---|---|---|
| The backend has no place for it, in the core or in an extension the proxy knows of | `NotSupportedByBackend` | `02102` |
| The backend can hold it, but the proxy does not map it | `NotSupportedByProxy` | `02103` if it names an extension, otherwise `02102` |
| The proxy uses an extension the server does not offer | `ErrorResponse` from `epp_*` | `02103` |

A mapper raises `NotSupportedByBackend` or `NotSupportedByProxy` (`core/capabilities/`) with the feature only, and
`map_request` names the backend of the application's `BackendProfile`: `… cannot be expressed in EPP`, `… can be
expressed in EPP, but not by this proxy`. What a backend can hold, where it differs between
backends, is a fact of the `BackendProfile` (`core/capabilities/backend_profile.py`), not a constant of a mapper: the
contact labels and how many registrants a domain has (`domains.check_contact_label`, `check_registrants`; further
registrants are contacts labelled `registrant`), the record types of a domain (`domain_dns`; `a`, `aaaa` and `mx`
records other than glue are `ZoneRecord`s the registry serves itself), the LGRs it offers (`domains.rpp_to_model`),
the transfer operations of each object (`TransferHandlers`, which answer 501 `02101` for one the backend lacks),
whether a restore takes a report (`domain_restore_report`), whether a read can show a domain's authInfo
(`domains.check_requested`, which refuses `includeElements=authInfo` otherwise), whether hosts are objects
(`domains.check_host_objects`, which refuses `nameservers`), whether a client sets statuses
(`domains.check_client_statuses`), what a contact holds (`contact_capabilities`: fax, localization, region, voice
numbers, authInfo, statuses, an organisation on an individual unless `contact_kind_held`, a person's name on an
organisation unless `contact.kind.supported`) and whether the backend renews (`renew_domain`, which sends no read
without). The domain mappers take the profile as the keyword `profile`, from `backend_profile()` in the handler; the
flows read it from the backend (`backend.profile`).

### Backend profile

The profile is data, not code. It is a tree, `<object>.<field>.<leaf>` and `<object>.processes.<process>.<leaf>`,
objects and fields by their RPP names, with leaves that mean the same under every object (`min_count`, `max_count`,
`<what>_supported`, `changeable`, `removable`; see
[testing.project.md](testing.project.md#selectors)). `LEAVES` in `core/capabilities/backend_profile.py` lists every
leaf and its type, and `BackendProfile` is the one class over the tree: an attribute is a node or a leaf
(`profile.contact.fax.supported`). It is built in two layers, merged in order (a map merges, a list or a value
replaces): the generic profile of the protocol, `src/settings/profiles/epp.yaml` (RFC 5730 to 5733, 5910 and 3915 as
the EPP Compatibility Profile takes them, with the gaps commented) or `rri.yaml` (DENIC RRI 5.0), then the server's own,
`rpp_backend_profile` in the config, which names the generic one with `extends` and states only what differs. Another
EPP server starts from `extends: epp` alone. `main.py` adds `lgrs` from the config (`Settings.lgrs`: the LGRs of
`rpp_idn_lgr_tables`, or `rpp_rri_lgr`). A missing, unknown or mistyped leaf stops the app at start.
`domainName.registrant.min_count`, `domainName.dns.min_count`, `contact.phone.min_count`, `contact.name.changeable`
and `contact.processes.delete.supported` are left to the registry to enforce and read by the test selectors only.

A value that is not in the form the backend requires (a phone number, the parts of a restore report) is a 400. The
mapper raises `BackendRequirement` (`core/capabilities/`) with `{backend}` in its text, and `map_request` names the
backend; a value read from the backend that cannot be shown is a 500 named the same way by `rpp_operation`.
Messages that flows and handlers make name the backend from its profile as well.

An extension the proxy does not know of cannot be told apart from no extension, so it
counts as the first kind. A PATCH that EPP could do once the proxy has read the object
is the second kind.

The third kind is known only from the EPP greeting, which mappers cannot reach, so the
`epp_*` function checks `supports_extension` and `raise_registry_error` renders the result.

## Wire contract

The frozen contract covers the OpenAPI paths and schemas, the core §18.1 result code
to HTTP status mapping, and the `RPP-*` headers. RPP result codes are EPP codes with a
leading `0`.

## Configuration

`load_settings` in [settings/load_settings.py](../../src/settings/load_settings.py) reads `config.yaml` (path
overridable via `RPP_CONFIG_FILE`, and an untracked `<name>.local.yaml` next to it replaces the keys it has) into
`Settings`, whose sections are `EppSettings` and `DiscoverySettings`; the section fields are the config.yaml keys.
`main.py` loads it once and passes each section on; nothing else imports `settings`. `rpp_backend_profile` is the
server's profile, see [Backend profile](#backend-profile). The EPP backend host and port
come from `rpp_epp_host` and `rpp_epp_port`, and `new_epp_client` in [main.py](../../src/main.py) uses them to open
the connection. `rpp_epp_ns_map` is the namespace map the EPP commands render with. `rpp_idn_lgr_tables` maps an LGR
name to an IDN table id, one to one. `main.py` turns it into `IdnTables`, which refuses a map that is not one to one,
so the app does not start with one. Without it no `lgr` is accepted. `rpp_epp_use_tls` (default `true`) connects
over TLS with the certificate and hostname verified. `rpp_epp_tls_insecure_skip_verify` (default `false`)
turns both checks off, for test backends only, and `main.py` warns when it is on. `rpp_epp_timeout`,
`rpp_epp_objects`, `rpp_epp_extensions` and `rpp_epp_connection_cache` are read into `EppSettings`, but nothing uses
them.

`rpp_backend` names the protocol (`Settings.backend`). `RriSettings` holds `rpp_rri_host`, `rpp_rri_port` (51131),
`rpp_rri_use_tls`, `rpp_rri_tls_insecure_skip_verify` (test backends only, main warns), `rpp_rri_timeout` (unused,
like the EPP one) and `rpp_rri_lgr`, the one LGR a client may name for DENIC's repertoire (gap Q11). There is no
RegAccId setting: it is taken from the login.

`rpp_base_url`, `rpp_tlds`, `rpp_environment_name` and `rpp_environment_status` are what the
discovery document (`GET /.well-known/rpp`, no authentication, no EPP) states. `rpp/handlers/discovery.py`
adds the RPP version, a constant, and the supported objects and profiles of the `BackendProfile`. Without all four, it
answers 500 (`02400`) and logs the keys, never the values. A setting is also missing when it has the wrong shape:
`rpp_base_url` must be an absolute `https` URL, `rpp_tlds` a non-empty list of non-empty strings. For EPP, `profiles`
is `epp-compatibility`, though `GET /profiles/{name}` is 501. The base URL is never taken from the request. The proxy
does not check the `version` parameter of the media type, so core §12's 406 is not enforced (#41). See
[spec-issues.md](../../.spec/spec-issues.md#discovery).

## Composition

[src/main.py](../../src/main.py) is the composition root. `compose(settings)` builds the app of one settings, and
`main` composes the settings it loads once as `main:app`; the integration tests compose one per test environment.
`rpp_backend` (`epp` by default, or `rri`) picks
`new_epp_backend` or `new_rri_backend` from `backends`, and builds the `BackendProfile` from the layers of the
settings, which both the backend and the app get; nothing else knows which backend runs.
`new_epp_backend` builds an `EppBackend` over the default
`EPPClient`, with the namespace map and the `IdnTables`, and `new_rri_backend` an `RriBackend` over an `RriClient`
on a `TCPClient` with payload-only framing. The chosen one is `new_backend`, the factory main passes to
[`SessionPool`](../../src/core/session/session_pool.py), which keeps one backend per user; `close()` logs them all out (the proxy does not call it on shutdown yet, #144). The pool goes to
`create_app` in [app.py](../../src/rpp/http/app.py), with the `BackendProfile` and the
`DiscoverySettings`, which the handlers read through [context.py](../../src/rpp/http/context.py). `create_app` hands
`SessionSecurityHandler` to Connexion through `security_map`, because Connexion would otherwise resolve the function
by name and it could not receive dependencies; the handler puts the user's backend into the token info (key
`backend`).

## Known debt

Do not copy these patterns (see [architecture.md](architecture.md#known-debt)).

- **Several classes per file:** `src/core/model/domain/domains.py` (11), `src/core/model/contact/contacts.py` (3),
  `src/core/model/shared/common.py` (3), `src/registry_adapter/common/transport/tcp_client.py` (2).
  Generated `registry_adapter/epp/xml/generated/` is exempt. (#20)
- **EPP limits in the mappers:** `rpp/mapping` refuses what EPP has no place for as constants of the mappers (pull
  transfers only, no reason on approve and reject, the parts of a restore report, the phone number form …), and its
  docstrings say so by name. With a second backend they become facts of the `BackendProfile`, as the contact labels
  did. `core`, `rpp/http` and `rpp/handlers` no longer name EPP, which `tests/unit/test_protocol_names.py` checks
  (#128).
