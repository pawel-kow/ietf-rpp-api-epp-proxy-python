## Installation

The proxy runs on every Python version that is still supported upstream, 3.11 to 3.15 at the time of writing
([devguide.python.org/versions](https://devguide.python.org/versions/)). `./test_python_versions.sh` checks this with
Docker: it installs `requirements-dev.txt` and runs a short set of unit tests on each of them.

Create and activate python virtual environment
```
python -m venv .venv
. .venv/bin/activate
```

Install modules
```
pip install -r requirements.txt 
```

For development, install `requirements-dev.txt` instead, which adds the tools of the checks.

## Running
```
cd src
uvicorn main:app
```

The proxy reads the file `RPP_CONFIG_FILE` names, else [config/environments/epp-docker.yaml](config/environments/epp-docker.yaml).
The configurations in [config/](config/README.md) are composed of layers, protocol, backend and environment, which a
file names with `include:`. An untracked `<name>.local.yaml` next to any layer changes it for one machine: its
mappings merge, its other values replace, and a top-level `null` unsets a key. For example
`config/environments/rri-mtest.local.yaml` with `rpp_rri_host: 172.17.0.9` points the MTEST environment at another
server.

The proxy speaks EPP to the registry by default; see [EPP or RRI behind the API](#epp-or-rri-behind-the-api) for
DENIC RRI.

The API documentation (Scalar) shall be available at http://127.0.0.1:8000/ui/, with a document per offered preset to choose
from (top left). Each preset's OpenAPI document (`/openapi/{preset-id}.json`, `.yaml`) is OpenAPI 3.1, with the body schemas
of that preset: the members of its extensions and the constraints of its profiles, as `GET /presets/{id}/schema` publishes
them, and the preset signalled as the server takes it (the `RPP-Preset` header or the media type), so a request sent from
it uses that preset. `/openapi.json` and `/openapi.yaml` are the default preset's. A document lists every operation of the
drafts' API contract, also those the server answers with 501. Two switches leave those out, against the contract, so each is off by
default; the demo configurations turn both on, so their document shows the planets and satellites only:

```yaml
rpp_openapi_omit_unheld_objects: true   # the operations on a data object the backend does not hold (501 02307)
rpp_openapi_omit_unimplemented: true    # the operations no handler serves (501 02101)
```

Requests to what they leave out still answer 501.

The username and password of HTTP Basic are the EPP login (`clID`/`pw`), and every request needs an `RPP-Cltrid`
header with a new value.

## EPP or RRI behind the API

`rpp_backend` in the config file chooses the protocol the proxy speaks to the registry:

| `rpp_backend` | Registry protocol | Settings it reads | Example config |
|---|---|---|---|
| `epp` (the default when the key is absent) | EPP (RFC 5730 ff.) over TCP | `rpp_epp_*` | [epp-docker](config/environments/epp-docker.yaml) |
| `rri` | DENIC RRI 5.0 (XML) over TCP | `rpp_rri_*` | [rri-mtest](config/environments/rri-mtest.yaml), [rri-local](config/environments/rri-local.yaml) |
| `sqlite` | no registry: a SQLite database, the demo objects Planet and Satellite | `rpp_sqlite_*`, `rpp_extensions` | [sqlite-demo](config/environments/sqlite-demo.yaml), and [extended](config/environments/sqlite-demo-extended.yaml), [bound](config/environments/sqlite-demo-bound.yaml), [inherit](config/environments/sqlite-demo-inherit.yaml) |

One process speaks one protocol: the one `rpp_backend` names is on, the other is off and its settings are ignored.
The RPP API is the same for both. With RRI, what RPP has no place for is in the `de.denic.rpp.rri` extension
([docs/rri/rri-extension.md](docs/rri/rri-extension.md)), and what RRI cannot hold or do answers 501: host objects,
client statuses, renew, transfers, contact deletion, a readable authInfo. See [docs/rri/](docs/rri/) for the mapping.

The `sqlite` backend is a test bed for protocol features, bare RPP over a database. It holds none of the drafts' data
objects (their paths answer 501 `02307`), but the planets and satellites of the demo extension
`org.example.rpp.extension.planets` ([docs/demo/planets-extension.md](docs/demo/planets-extension.md)), with create,
read, update, partial update, delete, availability and, for planets, the EPP-style transfer with its messages. The
extension is registered by the config (`rpp_extensions: [extensions.planets]`), and without it the proxy does not know it. Two more demo
extensions add an atmosphere to a planet and an orbit to a satellite (`extensions.planet_atmosphere`, `extensions.satellite_orbit`),
with demo profiles and presets for them; they are specified in [docs/demo/](docs/demo/).
The clients are `rpp_sqlite_clients`, a user and the `scrypt` hash of its password
(`echo -n secret | python -m registry_adapter.sqlite.hash_password`, from `src/`); the user is the sponsoring client.
```
cd src
RPP_CONFIG_FILE=../config/environments/sqlite-demo.yaml uvicorn main:app   # clients demo-a and demo-b, passwords demo-a-password ...
# the demo compositions in config/environments/: sqlite-demo (bare: the planets preset), sqlite-demo-extended (all three
# extensions, no binding), sqlite-demo-bound (the server binds profiles to presets), sqlite-demo-inherit (presets and
# profiles with several bases)
```

A config for RRI states at least:
```yaml
rpp_backend: rri
rpp_rri_host: rri.test.denic.de   # DENIC MTEST
rpp_rri_port: 51131
rpp_rri_use_tls: true
rpp_extensions:
  - extensions.rri                # the RRI extension (src/extensions/rri), which adds its preset `rri` and its leaves
rpp_backend_profile:
  extends: rri                    # the generic RRI profile, src/settings/profiles/rri.yaml
  presets: [base, rri]            # the RPP presets offered (src/rpp/schema/schemas/presets, and the extension's)
  default_preset: rri             # the one a request gets when it names none
  bound_profiles: {}              # per preset, the profiles this server binds to it: {rri: [my-policy]}
  informational_profiles: []      # the profiles the server checks itself: advertised, the proxy does not check them
rpp_preset_signalling: header     # how a client names the preset: the RPP-Preset header field (the default), or media-type
rpp_tlds:
  - de
```
A preset names extensions and the profiles of its definition (a profile constrains, an extension adds). A client names the
preset of a request with `RPP-Preset: preset=<id>;version=1.0` (core, Preset Signalling), or, with
`rpp_preset_signalling: media-type`, with the parameters of the media type, `Accept: application/rpp+json;
preset="<id>"; preset-version="1.0"` and the same in the `Content-Type` of every request, with content or without; without
it the request is under `default_preset`, with the header method, and under it as well with the media type method. The two
methods are not mixed. The response names the preset applied, in `RPP-Preset` or in its `Content-Type`. A request that breaks
a constraint of a profile that applies to its preset is 422 `02308`, and the error names the profile. Discovery lists the
presets (`GET /presets/<id>`, with the profiles of the definition and the bound ones) and the profiles (`GET /profiles/<id>`);
`GET /presets/<id>/schema` is the JSON Schema of the preset at this server, with the constraints of every profile that applies,
as `application/schema+json` and without authentication. `rpp_backend_profile.extends` names the generic profile of the protocol and defaults to `rpp_backend`. HTTP Basic is
passed through as the RRI LOGIN, as it is as the EPP login. DENIC lets in only addresses on the allowlist of the
RegAcc.

To switch a running proxy to the other protocol, restart it with the other config. To offer both, run two
proxies, each with its own config and port:

```
cd src
uvicorn main:app --port 8000                                                          # EPP, epp-docker
RPP_CONFIG_FILE=../config/environments/rri-mtest.yaml uvicorn main:app --port 8001     # RRI
```

In docker, name the config of the image (see [Running docker](#running-docker)):
```
docker run -d --name rpp-epp -p 8000:8091 --network epptest_epp_net pawelk/rpp_server_epp_proxy
docker run -d --name rpp-rri -p 8001:8091 -e RPP_CONFIG_FILE=/config/environments/rri-mtest.yaml \
  pawelk/rpp_server_epp_proxy
```

## Local EPP server

[EPP-server-docker](https://github.com/pawel-kow/EPP-server-docker) runs an EPP test registry (XPanel) in docker
compose. Its README has the details; in short:

```
git clone https://github.com/pawel-kow/EPP-server-docker.git
cd EPP-server-docker
git submodule update --init                  # the submodule URL uses SSH, so this needs a GitHub SSH key
docker compose -p epptest --profile setup up # once: provisions the database
docker compose -p epptest --profile setup down
docker compose -p epptest --profile run up -d
```

Use the project name `epptest` with every compose command: [epp-docker](config/environments/epp-docker.yaml) reaches
the server as `epp-server` on TLS port 743, a name that resolves only on the compose network `epptest_epp_net`. From the
docker host the server is on `localhost:7043` (TLS) instead. Its certificate is self-signed, so the config sets
`rpp_epp_tls_insecure_skip_verify`; never set it against a real registry.

It provisions two registrars, `foo`/`bar` and `baz`/`qux`, with the contact id prefixes `FO-` and `BZ-`, and
registers under the TLD `example`. It refuses a reused `clTRID`, also across sessions.

To run the proxy against it:

- **In the devcontainer:** the devcontainer joins the network when it starts. If the backend was not up then, join it
  by hand, then run the proxy as in [Running](#running):
  ```
  docker network connect epptest_epp_net $(cat /etc/hostname)
  ```
- **On the docker host:** put the host's address of the server in an untracked
  `config/environments/epp-docker.local.yaml`, which the default config takes:
  ```
  printf 'rpp_epp_host: localhost\nrpp_epp_port: 7043\n' > config/environments/epp-docker.local.yaml
  cd src && uvicorn main:app
  ```
- **In docker:** see [Running docker](#running-docker).

A quick check, a domain check as `foo`:
```
curl -I -u foo:bar -H 'Accept: application/rpp+json' -H "RPP-Cltrid: $(uuidgen)" \
  http://127.0.0.1:8000/domainNames/my-test.example/availability
```

For the integration tests, copy [.env.example](.env.example) to `.env` and fill in the `TEST_EPP_*` variables with
these registrars; see [docs/agents/testing.project.md](docs/agents/testing.project.md#backend).

## Deployment

To deploy on an Ubuntu host with Ansible (rootless Docker, a hardened image, one instance per configuration, the EPP
test server, TLS terminated by nginx), see [deploy/README.md](deploy/README.md).

## Building docker
```
docker build . -f ./.docker/Dockerfile -t pawelk/rpp_server_epp_proxy
```

The image holds [config/](config/README.md) at `/config` as it is at build time, and reads
`/config/environments/epp-docker.yaml` unless `RPP_CONFIG_FILE` names another. The `*.local.yaml` files stay out of
the image ([.dockerignore](.dockerignore)).

## Running docker
```
docker run --rm -p 8000:8091 pawelk/rpp_server_epp_proxy
```

The proxy listens on 8091 in the container, so the API documentation is at http://127.0.0.1:8000/ui/.

Against the [local EPP server](#local-epp-server), join the container to its network, where the built-in
epp-docker config finds it:
```
docker run --rm -p 8000:8091 --network epptest_epp_net pawelk/rpp_server_epp_proxy
```

With a config of your own, one file without `include:`, mount it and name it in `RPP_CONFIG_FILE`:
```
docker run --rm -p 8000:8091 -v "$PWD/my-config.yaml:/config/config.yaml:ro" \
  -e RPP_CONFIG_FILE=/config/config.yaml pawelk/rpp_server_epp_proxy
```

The path of `-v` is one on the machine of the docker daemon: in the devcontainer, which uses the host's docker, it is
a path on the host, not under `/workspaces`.
