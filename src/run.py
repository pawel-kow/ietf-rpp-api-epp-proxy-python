from app import app
from connexion.resolver import RelativeResolver

app.add_api("openapi.yaml", resolver=RelativeResolver('controller'))