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