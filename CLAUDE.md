# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

An RPP (Registration Protocol Proxy) server that exposes a REST/JSON API (the IETF RPP draft) and translates each request into classic EPP (RFC 5730/5731 etc.) commands sent over TCP to a backend EPP registry server. It is a stateless-by-default protocol bridge: RPP JSON in → EPP XML out → EPP XML back → RPP JSON out.

## Commands

```bash
# Setup
python -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

# Run the server (must run from src/ — the app resolves openapi.yaml and config.yaml relative to CWD)
cd src && uvicorn run:app        # Swagger UI at http://127.0.0.1:8000/ui/

# Tests (run from repo root; pyproject sets pythonpath=src and testpaths=tests)
pytest                                              # all tests
pytest tests/integration/test_from_file_definition.py   # the data-driven integration suite
pytest -k domain_update                             # single test group by substring
pytest "tests/integration/test_from_file_definition.py::test_from_file_definition[domain_update-test1-simple_update]"  # one case by id

# Docker
docker build . -f ./.docker/Dockerfile -t pawelk/rpp_server_epp_proxy
docker run --rm -p 8000:8091 pawelk/rpp_server_epp_proxy
```

Integration tests require a **backend EPP test server**, whose host/port come from `config.yaml` (`rpp_epp_host`/`rpp_epp_port`) via `basic_auth` in [src/controller/auth.py](src/controller/auth.py). In this devcontainer that is the `epp-server-docker-epp-server-1` container on port `700`, reached over the shared `epp-server-docker_epp_net` docker network (attached via `postStartCommand` in [.devcontainer/devcontainer.json](.devcontainer/devcontainer.json)). There is no mock; tests exercise the full RPP→EPP→RPP round trip against a live registry. Auth uses HTTP Basic, and the username/password are passed straight through as the EPP `clID`/`pw` login credentials.

## Request lifecycle / layered architecture

A request flows through distinct layers, each in its own package under `src/`. Understanding this chain is essential — a single feature (e.g. "domain update") touches every layer:

1. **`openapi.yaml`** — the API contract. Connexion routes operations to controller functions by `operationId` (e.g. `domains_Update` → `controller.domains.domains_Update`) via `RelativeResolver('controller')` in [src/run.py](src/run.py). **This file is generated** — see "Generated artifacts" below; do not hand-edit.

2. **`controller/`** — HTTP handlers. Parse request, call the RPP→model mapper, call the eppclient, map the EPP result back to RPP, and translate EPP result codes into HTTP status + `ProblemException`. This is where EPP result codes map to HTTP status (see [RPP_IMPLEMENTATION_NOTES.md](RPP_IMPLEMENTATION_NOTES.md): 2302→409, 2303→404, other client errors→400, server errors→500).

3. **`rpp_to_model_mapper/`** — converts inbound RPP JSON dicts ↔ internal `models` dataclasses. Validates every payload against a JSON Schema first via `validate_schema(...)` before mapping. Also does the reverse (`*_to_rpp`) and re-validates the outbound dict.

4. **`models/`** — the internal domain model (plain `@dataclass(kw_only=True)`), provider-neutral. `ResultCode` (an `Enum` of EPP codes with `(code, text)` tuples) and `OperationResponse`/`ErrorResponse` live in [src/models/response.py](src/models/response.py).

5. **`eppclient/`** — orchestrates one EPP operation: build XML → `send_and_get_response` → parse. `epp_*` functions return either a typed `*Response` model or an `ErrorResponse`; controllers branch on `isinstance`. [eppclient.py](src/eppclient/eppclient.py) is the raw TCP+XML client (login/logout, `_parse_epp_response` reads the `<result code>`; codes matching `1xxx` = success).

6. **`epp_to_model_mapper/`** — builds outbound EPP XML from models and parses inbound EPP XML into models. `epp_model/` holds xsdata-generated dataclasses for the EPP XSDs (domain-1.0, contact-1.0, secDNS-1.1, etc.). `commands/not_used/` is dead code — ignore it.

Key detail: `domains_Create`/`domains_Update` do not build their response from the create/update reply — they issue a **follow-up EPP Info** call and map that to RPP, because EPP mutation responses don't echo full object state.

## Generated artifacts — do not hand-edit

`src/openapi.yaml` and `src/rpp_schema_validator/schemas/*.json` are copied in from a sibling **TypeSpec** project by [copy_models.sh](copy_models.sh) (expects `../ietf-rpp-api-typespec/tsp-output/`). The JSON schemas are the single source of truth for request/response validation — schema names (e.g. `"Domain"`, `"DomainUpdateModel"`) are passed by string to `validate_schema`. If validation fails unexpectedly, check whether the schema and the mapper drifted; the fix usually belongs in the TypeSpec project, not here.

## Configuration

`Config` in [src/config.py](src/config.py) loads `config.yaml` at import time (path overridable via `RPP_CONFIG_FILE`). `rpp_epp_connection_cache` (default `false`) toggles between stateless per-request EPP connections and a cached, stateful connection. The EPP backend host/port are read from config (`rpp_epp_host`/`rpp_epp_port`) and used by `basic_auth` in `auth.py` to open the EPP connection.

## Test data format

The integration suite ([tests/integration/test_from_file_definition.py](tests/integration/test_from_file_definition.py)) auto-discovers every `*.json` under `tests/integration/test_case_data/<group>/` and parametrizes one test per file. Each file is a `steps` sequence (multi-step scenarios, e.g. create → update → verify) run against a Flask test client. Conventions:

- Placeholders `{random_name}`, `{random_id_10}`, `{test_start}` are substituted per run so tests are idempotent against a shared registry.
- Response body comparison is **subset + case-insensitive** (`recusive_compare_existing`) and lists are matched unordered — because EPP servers may uppercase domain/host names and reorder list entries (see [RPP_IMPLEMENTATION_NOTES.md](RPP_IMPLEMENTATION_NOTES.md)).
- `fields`/`headers` support condition dicts (`not_null`, `datetime_format_utc_and_delta`, …) via `evaluate_condition`.

To add a case, drop a new JSON file in the appropriate group dir; no Python changes needed. Add `"skip": "reason"` at the top level to skip one.

## Environment notes

- Runtime `python --version` here is 3.9, but the code uses 3.10+ syntax (`str | None`, `tuple[...]`, `dict[str,str]`). Use the `.venv` interpreter, which is a newer Python.
- The stack is Connexion 3 (ASGI) on Flask + Starlette middleware, served by uvicorn.
