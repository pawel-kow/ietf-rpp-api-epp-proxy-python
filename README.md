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

## Running
```
cd src
uvicorn run:app
```

Swagger UI shall be available at http://127.0.0.1:8000/ui/

## Building docker
```
docker build . -f ./.docker/Dockerfile -t pawelk/rpp_server_epp_proxy
```

## Running docker
```
docker run --rm -p 8000:8091 pawelk/rpp_server_epp_proxy
```