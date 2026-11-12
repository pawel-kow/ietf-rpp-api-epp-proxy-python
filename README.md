## Installation

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

The proxy speaks EPP to the registry by default. `rpp_backend: rri` in the config file makes it speak DENIC RRI 5.0
(XML) instead, with the `rpp_rri_*` settings; [config.rri-mtest.yaml](config.rri-mtest.yaml) is the one for DENIC's
test environment. One deployment speaks one protocol, and the RPP API is the same for both. What RRI cannot hold or
do answers 501: host objects, client statuses, renew, transfers, contact deletion, a readable authInfo. See
[docs/rri/](docs/rri/) for the mapping.

Swagger UI shall be available at http://127.0.0.1:8000/ui/

## Building docker
```
docker build . -f ./.docker/Dockerfile -t pawelk/rpp_server_epp_proxy
```

## Running docker
```
docker run --rm -p 8000:8091 pawelk/rpp_server_epp_proxy
```