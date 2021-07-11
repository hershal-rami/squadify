import os
from flask import Flask
from flask_session import Session
from .database import SquadConverter


app = Flask(__name__)

app.url_map.converters["squad"] = SquadConverter

app.config["SECRET_KEY"] = os.urandom(64)
app.config["SESSION_TYPE"] = "mongodb"
app.config["SESSION_MONGODB_DB"] = "squadify"

Session(app)


from . import routes
