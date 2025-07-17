from connexion import FlaskApp
from controller import *
from connexion.middleware import MiddlewarePosition
from starlette.middleware.cors import CORSMiddleware

app = FlaskApp(__name__)

app.add_middleware(
    CORSMiddleware,
    position=MiddlewarePosition.BEFORE_EXCEPTION,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
