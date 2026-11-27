# Architecture: project specifics

Generic rules are in [architecture.md](architecture.md).

## Module boundaries

`src/` holds a protocol-free core, the RPP adapter that receives requests, and the registry adapters, each split by
registry object (#120). The rules below are checked by `import-linter`.

### Structure

```
src/
├── main.py                  composition root, the only module that knows all others
├── api_docs/                serves the OpenAPI documents and the UI (Scalar, scalar_ui/ vendored) in front of the rpp app:
│                            docs_app (DocsApp), served_documents, ui_configuration; knows no other package
├── registry_setup.py        the extensions the settings name, registered, and the backend profile built with them
├── settings/                loads the configuration once into typed sections, which main.py passes on
│   └── profiles/            epp.yaml, rri.yaml, sqlite.yaml: the generic backend profile of each protocol (not the RPP presets and profiles)
├── registration/            the registry of the extensions a configuration names: stdlib only, knows no other package
├── extensions/<name>/       one extension (today `rri`, `planets`, `planet_atmosphere`, `satellite_orbit`): register_<name>.py, core/{model,ports,flows}/ and
│                            rpp/{dto,mapping,handlers,schema}/, see Registered extensions below
├── core/                    pure Python: no I/O, no framework, no protocol
│   ├── model/{shared,domain,contact,host,message}/
│   ├── result/              ResultCode, UnknownResultCode, OperationResponse, ErrorResponse
│   ├── capabilities/        BackendProfile, NotSupportedByBackend, NotSupportedByProxy
│   ├── ports/               RegistryBackend, *Gateway, ReplaceOutcome, ReplacementSteps, derived_update
│   ├── session/             SessionPool
│   └── flows/               read_back.py, mutation_result.py, sponsor.py, {domain,contact,host,message}/
├── rpp/                     receiving adapter: RPP over HTTP
│   ├── http/                app (create_app), rpp_app (RppApp), extension_paths (add_registered_paths), body_definitions, served_document,
│   │                        document_signalling, middleware/, validators/, security/, problem, headers,
│   │                        context, operation, preset_signalling, preset_middleware, request_presets,
│   │                        preset_selection, header_preset_signalling, media_type_preset_signalling, preset_header,
│   │                        media_range, native_accept
│   ├── handlers/            {domain,contact,host,message}/, shared/, discovery.py, presets.py, profiles.py
│   ├── mapping/             shared/, {domain,contact,host,message,discovery,preset,profile}/
│   ├── dto/                 the RPP dataclasses
│   ├── schema/              validator, schema_scope, request_schemas, effective_schema, definitions, offered_presets,
│   │                        preset_schemas, data_objects, extensions, schemas/ (generated; the
│   │                        Profile Schemas in profiles/ copied; presets/ and profiles/*.yaml written by hand)
│   └── openapi.yaml         (generated)
└── registry_adapter/
    ├── epp/
    │   ├── session/         EPPClient: greeting, login, extensions
    │   ├── xml/             codec (ns_map passed in), generated/
    │   ├── commands/        {domain,contact,host,message}/<operation>.py, shared/
    │   ├── gateways/        EppBackend, Epp*Gateway
    │   ├── idn_tables.py    lgr <-> EPP IDN table
    │   └── refusals.py, contact_refusal.py
    ├── sqlite/              the demo backend over SQLAlchemy: database, migrations, clients, the message queue, the
    │   │                    session (SqliteBackend); extensions/<name>/ holds the models and gateways of an extension
    ├── rri/
    │   ├── session/         RriClient: LOGIN (no greeting), LOGOUT, lock, re-login, RegAccId of the login
    │   ├── xml/             codec, generated/ (xsdata, from docs/rri/xsd by generate_rri_models.sh)
    │   ├── commands/        {domain,contact,message}/<operation>.py, shared/rri_command.py (run, CTID)
    │   ├── gateways/        RriBackend, Rri*Gateway (hosts: every command UNIMPLEMENTED)
    │   ├── extensions/<name>/  the RRI part of an extension: its commands and gateways, loaded by name (extension_part.py)
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
- Only `main` imports more than one adapter. Nobody but `main` and `registry_setup` imports `settings`: `registry_setup`
  is part of the composition root (it builds the registry and the backend profile from the settings, so that the test
  environments can build a profile without composing an app). `core`, `registration`, `rpp`, `extensions` and
  `registry_adapter` are forbidden to import `settings` by their contracts.
- `api_docs` imports no other package of the proxy, and no web framework but Starlette: it gets the documents as plain
  dicts, which `main` takes from the rpp app (`RppApp.openapi_documents`) and hands over. No package but `main` imports it.
- `registration` imports no other package of the proxy. No generic package (`core`, `rpp`, `registry_adapter`,
  `settings`, `registration`) imports `extensions`, but `registry_adapter/sqlite/extensions/<name>` imports the `core` of
  its extension and nothing else of it. An extension imports no registry adapter, settings or XML; its `core` imports
  the `core` of the proxy only; inside it `register_<name> → rpp → core`, `rpp: handlers → mapping → dto, schema`,
  `core: flows → ports → model`. The common part of `registry_adapter/sqlite` never imports the part of an extension
  (it loads it by name) and `registry_adapter/sqlite` stays independent of `epp` and `rri`.
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
| `rpp.http` | Object semantics, the backend protocol, how the documents are served and shown |
| `api_docs` | RPP beyond a document's `info.x-rpp-preset`: presets, signalling, schemas; the backends, the settings, Connexion |
| `registry_adapter.*` | HTTP, RPP JSON, OpenAPI, Problem Details, `includeElements`, config files |
| `registry_adapter.common` | Which protocol uses it, the model, the result codes |

### The check

`import-linter` checks the rules, one contract per rule, configured in `[tool.importlinter]` of
[pyproject.toml](../../pyproject.toml) and run with `PYTHONPATH=src lint-imports` (see
[process.project.md](process.project.md#checks-before-done)). A forbidden contract also follows indirect imports.
`main.py` is a module, which import-linter cannot take as a root, so an import of `main` is forbidden by name and what
`main` imports is not checked. `protocols-independent` keeps `epp`, `rri` and `sqlite` apart. Every
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
   Problem Detail (`handle_rpp_error`); a framework `HTTPException` (unknown path, wrong method) is converted by
   `handle_http_exception` and rendered through `handle_rpp_error`. `headers.py` builds the `RPP-*` headers. `context.py` is the only reader of
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
   the registry: `domains`, `contacts`, `hosts`, and `messages` are its gateways (`DomainGateway` …,
   each a `typing.Protocol`), and `extension(id)` the gateways of a registered extension (`KeyError` where the backend lacks it), `sponsor_id` is the id the registry stores as sponsor, and `profile` the `BackendProfile`. A
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
    domain's further holders are contacts labelled `registrant`, General Request and Abuse are contact references of
    the roles `generalRequest` and `abuse`, and `a`/`aaaa`/`mx` entries are `ZoneRecord`s. An IDN is sent with its U-label as `handle` and its
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
    update keeps the type RRI holds. A transfer request is CHPROV (`commands/domain/update.py`), with the domain's data
    from the `rri` extension and the AuthInfo in plaintext, so it is sent with `loggable=False`; its reply has no
    transfer state, so the gateway answers a process `serverApproved` by the gainer at the time of the reply
    ([rri-extension.md](../rri/rri-extension.md)). A contact of type REQUEST is a request contact
    (`RriRequestContactGateway`, `extensions/rri/`, the RRI part of the rri extension, which `RriBackend` gives by `extension("de.denic.rpp.rri")`), not a contact: each INFO answers 404 for a handle of the
    other kind, and a check is the contact CHECK, as both share the handles. Hosts, the other transfer operations, renew and
    contact delete answer `UNIMPLEMENTED_COMMAND`. Every queue
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
`latest` is implemented, see [spec-issues.md](../../.spec/spec-issues.md#transfer-process). Where the backend profile
offers an extension that adds members to `domainTransferProcess.create` (`de.denic.rpp.rri`), `domain_transfer_process` takes them
out of the request and converts them with `domains.rpp_to_model`, as a create's, into `DomainTransfer.domain`.

## RPP presets and profiles

An extension adds functionality, a profile constrains, and a preset is what a client signals: a named, versioned list of
extensions and of the profiles its definition includes, built on its base presets. A server binds further profiles to a
preset it offers (data-objects, `.spec/proposals/174-presets/`). All of this is the RPP layer's: a backend never sees a
preset, a profile or a schema, and no JSON reaches `core`.

**Definitions** (`rpp/schema/definitions.py`, `Definitions`, built once per app, so nothing is process-global): the files
`rpp/schema/schemas/presets/<key>.yaml` (`base`, `epp-compatible`) and `profiles/<key>.yaml` (`epp-compatibility`,
with its Profile Schema `epp-compatibility.schema.json`, copied from `.spec/` by `copy_models.sh`), and what the registered
extensions bring (`RegisteredExtension.presets` and `.profiles`, as the same files state them; the rri extension brings the presets `rri` and `rri-strict` and the profile DENIC RRI that the second applies (docs/rri/rri-profile.md, rri-strict-preset.md; `config/backends/rri.yaml` and the deploy template offer both, `rri` is the default), the planets extension brings
the preset `planets` and the demo profiles and presets that need it, and `planet_atmosphere` and `satellite_orbit` those that need them, each specified under [docs/demo/](../demo/), #179). A definition is the same on every server. A definition that refers to an extension that is not registered is read only where a configuration offers it: an app that registers `planets` and `planet_atmosphere` does not know the presets of `satellite_orbit`. A reference to a base preset, a base profile, an extension
or a required extension is an identifier and an exact version; an identifier denotes one definition, whatever its kind.
`GET /presets/{id}` and `GET /profiles/{id}` publish them (`handlers/presets.py`, `handlers/profiles.py`,
`mapping/preset/`, `mapping/profile/`), flattened.

**Offered presets.** The `presets` (keys), `default_preset` and `bound_profiles` (`{preset key: [profile keys]}`, one map leaf)
leaves of the `BackendProfile` say which a server offers and binds, from `epp.yaml`, `rri.yaml` or `sqlite.yaml` and what
`rpp_backend_profile` of the config states. `create_app` builds `OfferedPresets` (`rpp/schema/offered_presets.py`) and stops
on a wrong choice, naming what conflicts: an unknown preset or profile, a preset offered twice, the default not offered,
a binding of a preset that is not offered or of a profile twice or one the preset already includes, a cycle, one extension in
two versions (also through two bases), an extension the proxy does not implement in the version the preset pins or the backend
does not hold, a profile (also a bound one, and through its base profiles) that requires an extension its preset lacks, a
Profile Schema that declares a property its target does not (`profile_schema_walk.py`, at any depth), that constrains a
definition that does not exist, or whose `$defs` keys clash with RPP's, an extension's or another profile's, and an Extension
Schema that is not additive (`extension_additivity.py`, a whitelist, see [spec-issues.md](../../.spec/spec-issues.md#presets-profiles-and-extensions)), and an
`informational_profiles` key that is unknown, named twice or applied by no offered preset. Inheritance is a union without overriding (`preset_flattening.py`),
each item once; the applicable profiles of a preset are its own, the bound ones and the base profiles of all, bases first.

**Informational profiles.** `informational_profiles` (profile keys) names the profiles the server checks itself (#232): they
apply and are advertised as before (discovery, `GET /presets/{id}`, `/profiles/{id}`, the Preset Schema), but the proxy does not
check a request against them, and the server's answer stands for what they forbid. `OfferedPreset.checked` is the applicable
profiles without them, and the `SchemaScope` of a preset is built from these only, so step 2 below, `profiles_apply()` and the
refusal of a removal know only the profiles the proxy checks. Only the profile named is informational: its base profiles are
checked unless they are named too. epp-docker names `epp-compatibility`: an EPP server enforces what the profile takes from EPP.

**Signalling** is `rpp_preset_signalling` (`Settings.preset_signalling`, default `header`), and
`preset_signalling(method, presets)` in `rpp/http/preset_signalling.py` gives the class of the method. Each has
`resolve(scope)`, the one place that chooses the preset, `announce(send, selection)`, which shows the applied preset in the
response, and `problem_headers`. A request has a `PresetSelection` (`rpp/http/preset_selection.py`): the `request` preset the
request is read under (its parsing, checking, routing and backend command), and the `response` preset (what the response shows
and its media type).

**`header`** (`HeaderPresetSignalling`) reads `RPP-Preset`, an RFC 9651 Dictionary (a repeated header's lines combined with a
comma, the last repeated key winning) parsed by `http-sfv` and checked in `rpp/http/preset_header.py`: the `preset` member is a
Token, its `version` parameter a Decimal (compared as a number, so 1.10 is 1.1). A request without the header gets the default
preset (core RC1), for the request and the response alike. A value it cannot read, a missing member or parameter, a preset or
version the server does not offer, or preset parameters on an `application/rpp+*` media range of `Accept` or `Content-Type`
(both methods in use) are a 400 with `02005`, `02003`, `02004` and `02001`. It adds `RPP-Preset` with the applied preset and
version to the response, with `RPP-Preset` in `Vary` (`handle_rpp_error` does it for the Problem Details an outer handler renders).

**`media-type`** (`MediaTypePresetSignalling`; `rpp/http/media_range.py` parses the media ranges) takes the request preset from the
parameters `preset` and `preset-version` of the `Content-Type` of every request, with content or without, and the response
preset from the `Accept` by weight. The request preset alone governs routing, validation, the mappers and the backend command;
the `Accept` governs only the response. `application/rpp+json` with the parameters stands for that preset, one without them for
the default preset, `application/*` and `*/*` for every offered preset. The most specific range gives a preset its weight, a
weight of 0 excludes it, the highest weight is answered, and on a tie the request preset if it is among the tied ones, else the
first range (a wildcard means the default preset). Refusals, each with `Vary: Accept`: 415 `02004` for a preset or version of
the `Content-Type` that is not offered, 406 `02004` when no preset of the `Accept` is offered, 400 `02001` when the request preset
is not listed in the `Accept` and when the `RPP-Preset` header is sent (both methods in use), 400 `02003` for a `preset` without
its `preset-version` or the reverse, 400 `02005` for a value that does not parse. The response media type carries the parameters
of the response preset; there is no `RPP-Preset` response header.

Every response of the rpp app also lists `Origin` in `Vary`: Starlette's `CORSMiddleware` (1.x, `allow_origins=["*"]` with
`allow_credentials=True`) mirrors the `Origin` of a request in `Access-Control-Allow-Origin` and adds `Origin` to `Vary`, after
what the signalling put there (so `Vary: Accept, Origin` under `media-type`). The tests check that `Vary` lists what the
signalling puts there, not its whole value (`list_contains`, see [testing.project.md](testing.project.md#test-data-format)).

**Preset Schema.** `create_app` builds `PresetSchemas` (`rpp/schema/preset_schemas.py`) once per app, so once per uvicorn worker,
at startup: for each offered preset a `SchemaScope` (`rpp/schema/schema_scope.py`) with the validators of every definition for
the preset's extensions without its applicable profiles, with those the proxy checks, and one per profile where there are several (to name the
profile a failure belongs to), and the document (json §Preset Schema). `rpp/schema/effective_schema.py` composes it: the
definitions of the bundle, the extension definitions and the Profile Schemas' `$defs` under their keys, a definition an
extension extends or a profile constrains the `allOf` of the base definition in place and the references to the extension and
profile sub-schemas, and an extension sub-schema a profile constrains the `allOf` of itself in place and the references to the
profile sub-schemas. The published document has no `unevaluatedProperties` (json §Preset Schema: a validator adds them), the
validators have them injected at every object-schema node. A request only looks a validator up. `GET /presets/{id}/schema` is
a Direct Access data element in its native media type: `application/schema+json`, no authentication, a 404 `02303` for a preset
not offered, and a 406 `02004` where `Accept` is neither the type, a range that includes it nor absent (core §Native Media
Types). It is outside preset signalling in both methods (core RC7): `PresetMiddleware` exempts it (no selection, no refusal, no
`RPP-Preset`), `RPP-Cltrid` is optional and echoed. `$id` is `rpp_base_url` plus the path, and only where discovery would accept
the base URL (`rpp/schema/https_url.py`).

**Two-step validation** (json §Profiles and Validation). `rpp_operation` makes the schemas of the request's preset the
mappers' own for the handler (`rpp/schema/request_schemas.py`, a context variable set in the handler's thread), so no mapper is
passed it. `validate_schema(name, data, extensions)` is the preset schema alone (a failure is the `ValidationError` or `ValueError`
that `map_request` makes a 400, as before). `validate_request_schema` is for what a client sent: step 1 as `validate_schema`, then
step 2 against the schema with the applicable profiles the proxy checks, whose failure is a `ProfileConstraintViolation` and answers 422 `02308`
with `profile` and `paths` in the error (`profile_constraint_problem` in `rpp/http/problem.py`; the reason never holds a value of
the request). A patch or a replacement is validated as the object it results in (`patched=True`) and a failure that concerns a
read-only member of the base definition, which the server manages, is not the client's; under a preset with applicable profiles the proxy checks, a patch of a contact, domain or host runs the same conversion that needs no read as without profiles (so it is refused alike), and is then applied to the object read for it (without such a profile it is sent as a partial update, and the server decides an item added twice or removed while absent); the native patch
of an extension (no read) checks the value of each operation as the member it sets and refuses the removal of a member a profile requires, see [spec-issues.md](../../.spec/spec-issues.md#two-step-validation-of-a-patch).
A mapper runs the checks that RPP or an extension states in prose and the schema cannot express after step 1 and before `validate_request_schema` (as `contacts.check_rpp_rules` does for the JSContact profile), so that a request that breaks one is refused as RPP defines it, under every preset, and not with 02308 (core §Extensions and Profiles of a Request, core.md:235); the profiles of an extension (the demo presets on planets, #179 and #180) follow this too. A response is validated with the preset schema without profiles, never with them. The prose constraints of a profile keep
today's behaviour (the mapper's 501 or the backend's error), as does a request under a preset without the profile.

`PresetMiddleware` (after the authentication) stores the selection in the request context (`preset_selection()`) and refuses a
routed operation on a data object of an extension that the request preset does not contain (400 `02001`, the code the proxy gives
to content that does not conform, core RC4) and on one the backend does not hold (501 `02307`). `request_profile()` is the backend
profile as the request is read under (`RequestPresets`): its `extensions` those of the request preset, so the combined schema of
[RPP extensions](#rpp-extensions) holds only them (guidelines §8.6); `response_profile()` is the same for what a response shows.
Discovery lists the presets (read view), the profiles applicable to them (reference view) and the extensions of the presets.
The extension paths exist for the extensions of every offered preset, so those of another are a 404.

## RPP extensions

An RPP extension (json §7) is a schema file in `.spec/`, copied by [copy_models.sh](../../copy_models.sh) to
the package of the extension that registers it (`src/extensions/<name>/rpp/schema/`, see
[Registered extensions](#registered-extensions)), and specified under `docs/` as
[specification.project.md](specification.project.md#kinds-of-specification) describes. `rpp/schema/extensions.py` holds those registered (`RppExtension`): the
Extension Object discovery states, the definitions each adds to a base definition, and the data objects it defines
(`objects` of `rpp:extension`). A deployment offers those of its offered presets; `create_app`
refuses one the proxy does not know or the backend does not hold. `validate_schema(name, data, extensions=profile.extensions)` takes the validator the app built for the
effective schema of the preset (json §7.2, composed with `allOf`, see [RPP presets and profiles](#rpp-presets-and-profiles)), and `added_members` names the members an extension adds, so a mapper names
no extension. Without the extension those members are undeclared, a 400 as before. An extension's own objects are
validated by the names a base object's definitions would have (`requestContact.create` for
`ext.rri.requestContact.create`).

The objects a registered extension defines get their paths in `create_app` (`add_registered_paths`): the `openapi` of the
extension builds its fragment from the OpenAPI document of the drafts. The rri extension
(`extensions/rri/rpp/schema/openapi_fragment.py`) copies the paths of the base object whose uniform interface its
`requestContact` shares (`contact`, without its processes) under the plural of the object's identifier (core §16.1), with
their own operationIds (`requestContacts_read`, the handler module named by `x-openapi-router-controller`) and plain object
schemas, as the mappers validate with the extension's. Without the extension the paths do not exist (404). An extension that
adds members to a domain name (or to the request of its transfer) registers a mapper in `DOMAIN_MEMBERS`
(`rpp/mapping/domain/domain_members.py`, a `MemberMappers` of `rpp/mapping/shared/member_mappers.py`, process-global and
idempotent like the planets' ones): the rri extension's (`extensions/rri/rpp/mapping/request_contact_members.py`) maps the
request contacts `generalRequest` and `abuse` to and from contact references whose role is the member's name, so the core and the
RRI adapter hold them as roles; `contacts` does not show them, and a PATCH of one reads the domain first. A mapper may also have a `check`, which runs after step 1 of the validation and before step 2 (the rri extension's refusal of the labels `generalRequest` and `abuse` of `contacts`, 501, under every preset). A patch applied to the object read for it refuses the removal of a whole member that an applicable profile requires (`rpp/mapping/shared/profile_removals.py`).

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

`LineFeedPathMiddleware` in `rpp/http/middleware/` is added before routing, inside Connexion's exception handling and
before security. A path with a line feed is not matched by Connexion's mount pattern (`.` does not match `\n`) and
used to fall through to Flask as a 500, so the middleware raises a 404, which `handle_http_exception` renders as a
404 Problem with 02001, as for an unknown path (detail `Not Found`) (#98). Only the line feed is refused. The paths of
the served documents and the UI never reach it: `api_docs` serves them in front of the rpp app, so `/ui/` or `/openapi.json`
followed by a trailing line feed still serves them.

**The OpenAPI document served** (#204). Connexion routes with the generated spec, OpenAPI 3.0, which is all it loads
(Connexion 3.2 and 3.3 refuse `openapi: 3.1.0`). What `/openapi.json`, `/openapi.yaml` and `/ui/` serve is another document,
OpenAPI 3.1, which `served_document` (`rpp/http/served_document.py`) makes when the app is built: the routing spec (with the
extension paths), the `$defs` of the default preset's Preset Schema under `components/schemas` by their keys (references
rewritten from `#/$defs/`), each body that stands for a definition pointing at the preset's (`domainName.create`, an extension's
own object at its key: `ext.rri.requestContact.create`), the schemas nothing refers to any more left out, and `info.x-rpp-preset`
naming the preset. It is the same as `GET /presets/{id}/schema` publishes, profile constraints included. A body of no
definition (`protocol.PartialUpdate`) or of one the default preset lacks keeps its generated schema.
**A document per offered preset** (#205): `/openapi/{preset-id}.json` and `.yaml`, outside the RPP paths, made the same way from
each preset's Preset Schema (`preset_documents` in `app.py`, the default preset's first), with the objects of the extensions the
preset does not contain left out (`outside_the_preset`: a request to them is a 400 under it), and the preset stated as the
server's signalling takes it, so that a client or the UI sends it: the signalling method's `state_in` (`HeaderPresetSignalling`:
`RPP-Preset` required, with the preset as its only value and default; `MediaTypePresetSignalling`: every RPP body keyed by
`preset_media_type`, the media type a response is typed with, every operation without a request body given a required
`Content-Type` header parameter of it, as such a request's preset is that of its `Content-Type` (OAS 3.1 has the parameter
ignored, Scalar sends it), and no `RPP-Preset` parameter), with the places in the document
found by `document_signalling`. `/openapi.json` stays the default preset's and states no preset.
Two switches (`OpenApiSettings`, off by default, a deviation from the drafts' API contract) leave operations out of it:
`rpp_openapi_omit_unheld_objects` those on a data object the backend does not hold under the default preset (by the first path
segment, `collections` in `extension_paths`), `rpp_openapi_omit_unimplemented` those no handler serves
(`ExtensionResolver.implements`). A path left without an operation goes, a tag no operation has, and every schema nothing refers to,
the Preset Schema's definitions too (`omitted_operations` in `app.py`, `served_document(omit=...)`); in a preset's document, by
the objects that preset holds. Routing does not change: those requests answer 501 as before. The demo configurations turn both on.
**Serving them** (#205) is no part of `rpp`. The rpp app (`RppApp`, a `FlaskApp`, built by `create_app` without Connexion's
`SwaggerUIMiddleware`) serves no document and no UI; it only gives them, `openapi_documents()`: the default document first, then
one per offered preset, copies made when the app is built, so Connexion's response validation, which writes `components` into
the response schemas of the spec its middlewares share (#193), does not reach them. `main.compose` puts `DocsApp` (`api_docs`)
in front of it (`Composition.app` is what uvicorn serves, `Composition.rpp_app` the rpp app). `DocsApp` serves `/openapi.json`,
`/openapi.yaml`, `/openapi/{preset-id}.json` and `.yaml`, each with the base path of the request (`root_path`) in `servers`
and readable from any origin (CORS), a preset it has no document of a plain 404, and `/ui/`; every other request and the
lifespan go to the rpp app. `/ui/` is Scalar (`@scalar/api-reference`, `api_docs/scalar_ui/`; the version and how to update
are in its README.md), with a source per preset document and `UI_CONFIGURATION` (`ui_configuration.py`): only its API
reference and test client, nothing of Scalar's platform (developer tools, AI agent, MCP, telemetry, remote fonts, the hosted
client's link, which `index.j2` hides), so the page loads nothing from another origin; snippets HTTP/1.1 and curl.

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
OpenAPI allows it, which Connexion's validators do not. The handler then gets an empty dict. `mark_body_definitions`
(`rpp/http/body_definitions.py`) marks each body schema of the routing spec whose definition some offered preset has with
`x-rpp-definition` next to its `$ref` (Connexion keeps it when it resolves the reference): `gen.<definition>` and
`ext.<definition>`, named as the mappers validate with it. Such a body is validated with that definition of the request's preset
(`RequestSchemas`, which `PresetMiddleware` puts in the request context), JSON Schema 2020-12 without profiles: a failure is a 400
`02001`, as the mappers' first step. The profiles stay the mappers' second step (422 `02308`), which knows what a patch or a
replacement results in. A response is validated with the response preset's definition, or the request preset's for an object
only the request preset has (as it is rendered). Any other body is validated by Connexion with its schema (Draft 4). The detail
of a refusal is the message only (a response's: the definition), never the body.

### Registered extensions

An extension of the proxy's own that is not built into the generic code is registered by the configuration: `rpp_extensions`
lists the module paths of the extension packages (`extensions.planets`), and `registry_setup.load_registry` imports
each and calls its `register(registry)` ([registration/](../../src/registration/)). The module registers one
`RegisteredExtension`, every element of the pipeline as data, and imports nothing of an adapter:

| Element | Is read by |
|---|---|
| the RPP extension schema, the data model of its objects (Visibility) | `rpp.schema` (`register_all`), process-global, keyed by extension id, so registering twice is no change. Nothing registers by import; a process that composes no app with the extension never sees it |
| the OpenAPI fragment of its paths (built from the OpenAPI document of the drafts), and the package of its handlers (every operationId is a fully qualified function name, or names the module of its handler) | `create_app` (`add_registered_paths`, `ExtensionResolver`), per app |
| the presets and the profiles it brings | `Definitions.load(registry)` in `create_app`, per app: nothing of them is process-global, and an app without the extension does not know them |
| its objects | `PresetMiddleware` and discovery, through the extension's schema |
| its part of a backend (`backend_parts`) | the backend: the SQLite backend imports `registry_adapter.sqlite.extensions.<name>`, which has `PART` (its tables, in a metadata of their own, with a schema version) and `gateways(context)`; the RRI backend imports `registry_adapter.rri.extensions.<name>`, which has `gateways(client)` |
| the leaves it adds to the backend profile (`objects`, `extensions` and `presets` are added to the generic profile's, other leaves are new) | `BackendProfile.from_layers(..., extra_leaves=...)`: the list of leaves stays closed, and without the extension a leaf of it is unknown |

The demo configurations compose the three demo extensions differently (README, [testing.project.md](testing.project.md#the-demo-configurations)):
`config/environments/sqlite-demo.yaml` (planets only), `sqlite-demo-extended.yaml`, `sqlite-demo-bound.yaml` (profiles bound to presets) and
`sqlite-demo-inherit.yaml` (several bases). A configuration that cannot hold, a binding without a required extension, a cycle or one
extension in two versions, stops the app at start naming the conflict; those are in `tests/refused_configs/`.

A backend gives the gateways of an extension by its id, `RegistryBackend.extension(extension_id)` (a `KeyError` where the
backend does not hold it), so no backend names an extension. An extension the configuration names that does not import,
has no `register`, has a definition named as a base definition or as another extension's, or has no part in the
configured backend, stops the app. The extension schema and the data model are process-global (registration is idempotent); what depends on the configuration is
per app: the presets, the profiles, the effective schema and the validators (`PresetSchemas`), see
[RPP presets and profiles](#rpp-presets-and-profiles).

A full and a partial update are native in the gateways of the planets extension (`replace(replacement)` and
`patch(id, changes)`, one unit of work each: lookup, sponsor and state checks, write, and the invariants of the result,
`02004` when broken), so there is no read-modify-write across requests. `rpp/mapping` translates a JSON Patch (json
§5.2) into `PlanetChanges` or `SatelliteChanges` (members to set, `cleared`), after checking each value against the update
schema: no JSON Patch, JSON pointer, `@type` or JSON dict reaches `core` or a backend. Another extension adds members to a
planet or a satellite without editing these classes: `extensions` of the replacement, the change set and the read model
maps its extension id to a typed object of its own `core`, and its SQLite part gives a `MemberHook` (`HOOKS` of its module,
`{object: hook}`) that the planets gateways call in the same unit of work. The rpp side is a `MemberMapper` (JSON members to the
typed object, to the typed changes of a patch, and back) that the extension adds in its `register` to `PLANET_MEMBERS` or
`SATELLITE_MEMBERS` (`extensions/planets/rpp/mapping/object_members.py`, process-global and idempotent as the schema registry): the
planets mappers take the members of the extensions of the request's preset out of the body after step 1, so a member of another
extension is undeclared (400), and a read shows those of the extensions of the response's preset (`response_profile()`, which differs from the request's with media-type signalling). A patch changes such a member as a whole (`/atmosphere`, `/orbit`),
a deeper path is 400. A full update carries `scope`, the extensions of the request's preset: the gateway replaces the members of
those, and removes one the request omits, and keeps the members of the others (`planet-atmosphere` and `satellite-orbit`, the
demo extensions that use it, are in [docs/demo/](../demo/)). An Extension Schema may extend a definition of another extension,
keyed `<$id of the owner>#/$defs/<definition>`: the owner must be in the preset (checked at start, naming both), and the
additivity check reads the owner's definition. An extension without data objects registers no `handlers` and no `openapi`.

The SQLite backend (`rpp_backend: sqlite`, [config/backends/sql.yaml](../../config/backends/sql.yaml)) is made as a test bed: the clients
are `rpp_sqlite_clients` (user to a `scrypt$...` hash, made by `python -m registry_adapter.sqlite.hash_password`, compared
in constant time; the user is the sponsoring client; `ClientDirectory` checks each hash with `check_hash` at start, and a
hash that cannot be used stops the app with a `ValueError` naming the client and never the hash, as `settings` may not
import an adapter), the database is `rpp_sqlite_url` (a file, or `sqlite://` in
memory), and every unit of work holds one lock. A file may be shared by the worker processes of one instance (#184): it
is in WAL mode, every unit of work begins `IMMEDIATE` (pysqlite's own transaction handling is off, as it would let a read
go stale before the first write), and waits for the lock of another process up to a busy timeout. The tables of each
part are created at start with their schema version (`schema_versions`), in one such transaction, so workers starting
together on a new file create them once; a version that differs stops the app: there is no migration yet. Its generic profile
(`settings/profiles/sqlite.yaml`) holds none of the drafts' objects, so their paths answer 501 `02307` from
`PresetMiddleware`; the stub gateways of those objects (`UnsupportedGateway`) are never what answers. The message queue
holds the events of a transfer (`TransferEvent`, object type `planet`). The planets extension
([docs/demo/planets-extension.md](../demo/planets-extension.md)) follows EPP for the transfer of a planet (RFC 5731
section 3.2.4): a pull that waits for the sponsor, its satellites have no sponsor of their own and so move with it, and
only the planet's events queue messages.

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
the transfer operations of each object (`TransferHandlers`, which answer 501 `02101` for one the backend lacks), the
RPP extensions it offers (`extensions`, see [RPP extensions](#rpp-extensions)),
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
`rpp_backend_profile` in the config, which names the generic one with `extends` and states only what differs, among it the RPP presets the server offers (`presets`, `default_preset`) and the profiles it binds to them (`bound_profiles`, one map leaf: `{preset key: [profile keys]}`), and the profiles it checks itself (`informational_profiles`). Another
EPP server starts from `extends: epp` alone. `main.py` adds `lgrs` from the config (`Settings.lgrs`: the LGRs of
`rpp_idn_lgr_tables`, or `rpp_rri_lgr`). A missing, unknown or mistyped leaf stops the app at start.
`domainName.registrant.min_count`, `domainName.dns.min_count`, `domainName.generalRequest.*` and
`domainName.abuse.*` (how many request contacts of the role a domain has: 0 to 1, leaves the rri extension adds, so a profile without it has none),
`contact.phone.min_count`, `contact.name.changeable` and `contact.processes.delete.supported` are left to the registry
to enforce and read by the test selectors only.

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
leading `0`. The document served is OpenAPI 3.1 with the default preset's body schemas, a decision of #204, and each offered preset
has one of its own (#205); the routing spec stays the generated 3.0.

## Configuration

`load_settings` in [settings/load_settings.py](../../src/settings/load_settings.py) reads the file `RPP_CONFIG_FILE`
names, else `config/environments/epp-docker.yaml` of the repository (found from the module, not the working directory),
into `Settings`, whose sections are `EppSettings` and `DiscoverySettings`; the section fields are the configuration
keys. The file is resolved by [settings/layered_yaml.py](../../src/settings/layered_yaml.py) (#217,
[config/README.md](../../config/README.md)): its `include:` layers in order, then the file, then the untracked
`<name>.local.yaml` of each layer; mappings merge, other values replace, and a top-level key that resolves to `null` is
absent. A key the proxy does not know is ignored, with a warning naming the file for an `rpp_*` one. The test helper
resolves the test environment descriptors with the same module. `rpp_protocol_config` (`Settings.protocol_config`) is
what the registry does where its protocol leaves the choice to the server; the proxy keeps it but does not use it, and
the integration suite reads it as the facts of its selectors.
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

`rpp_extensions` lists the extension modules to register, see [Registered extensions](#registered-extensions). `OpenApiSettings` holds
`rpp_openapi_omit_unheld_objects` and `rpp_openapi_omit_unimplemented` (both `false` by default, a value that is not a boolean
stops the configuration), see [The OpenAPI document served](#request-lifecycle).
`SqliteSettings` holds `rpp_sqlite_url` and `rpp_sqlite_clients`. `rpp_backend` names the protocol (`Settings.backend`). `RriSettings` holds `rpp_rri_host`, `rpp_rri_port` (51131),
`rpp_rri_use_tls`, `rpp_rri_tls_insecure_skip_verify` (test backends only, main warns), `rpp_rri_timeout` (unused,
like the EPP one) and `rpp_rri_lgr`, the one LGR a client may name for DENIC's repertoire (gap Q11). There is no
RegAccId setting: it is taken from the login.

`rpp_base_url`, `rpp_tlds`, `rpp_environment_name` and `rpp_environment_status` are what the
discovery document (`GET /.well-known/rpp`, no authentication, no EPP) states. `rpp/handlers/discovery.py`
adds the RPP version, a constant, the data objects the `BackendProfile` holds (the presets name none), and the offered presets, the profiles applicable to them and the extensions of the presets (the discovery mapper takes them from `OfferedPresets`, and core `Discovery` has none). Without all four, it
answers 500 (`02400`) and logs the keys, never the values. A setting is also missing when it has the wrong shape:
`rpp_base_url` must be an absolute `https` URL, `rpp_tlds` a non-empty list of non-empty strings. `presets` are the
RPP presets the server offers, `profiles` the profiles applicable to them and `extensions` those of the presets, see [RPP presets and profiles](#rpp-presets-and-profiles). The base URL is never taken from the request. The proxy
does not check the `version` parameter of the media type, so core §12's 406 is not enforced (#41). See
[spec-issues.md](../../.spec/spec-issues.md#discovery).

## Composition

[src/main.py](../../src/main.py) is the composition root. `compose(settings)` builds the app of one settings, and
`main` composes the settings it loads once as `main:app`; the integration tests compose one per test environment.
`rpp_backend` (`epp` by default, `rri`, or `sqlite`) picks
`new_epp_backend`, `new_rri_backend` or the SQLite factory from `backends`, after `load_registry` has registered the
extensions of `rpp_extensions`, and builds the `BackendProfile` from the layers of the
settings, which both the backend and the app get; nothing else knows which backend runs.
`new_epp_backend` builds an `EppBackend` over the default
`EPPClient`, with the namespace map and the `IdnTables`, and `new_rri_backend` an `RriBackend` over an `RriClient`
on a `TCPClient` with payload-only framing. The chosen one is `new_backend`, the factory main passes to
[`SessionPool`](../../src/core/session/session_pool.py), which keeps one backend per user; `close()` logs them all out (the proxy does not call it on shutdown yet, #144). The pool goes to
`create_app` in [app.py](../../src/rpp/http/app.py), with the `BackendProfile` and the
`DiscoverySettings`, which the handlers read through [context.py](../../src/rpp/http/context.py). `create_app` hands
`SessionSecurityHandler` to Connexion through `security_map`, because Connexion would otherwise resolve the function
by name and it could not receive dependencies; the handler puts the user's backend into the token info (key
`backend`). The spec's `BearerAuth` gets `BearerRefusingSecurityHandler`, which skips the scheme as Connexion does
for one without a function, without its warning per operation (#189): a Bearer token is unauthenticated, 401.

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
