__version__ = "0.1.0"

from flask import Flask

app = Flask(__name__)


@app.route("/")
def homepage():
    return "Hello, World!"


@app.route("/<uuid:mix_id>")
def view_mix():
    return "Hello, World!"


@app.route("/api/new", methods=["POST"])
def new_mix():
    return "Hello, World!"


@app.route("/api/add", methods=["POST"])
def add_to_mix():
    return "Hello, World!"


@app.route("/api/finish", methods=["POST"])
def finish_mix():
    return "Hello, World!"
