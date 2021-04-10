__version__ = "0.1.0"

from flask import Flask
from flask import render_template

app = Flask(__name__)


@app.route("/")
def homepage():
    return render_template("index.html")


@app.route("/<uuid:squad_id>")
def view_squad(squad_id):
    return "Hello, World!"


@app.route("/api/new", methods=["POST"])
def new_squad():
    return "Hello, World!"


@app.route("/api/add", methods=["POST"])
def add_to_squad():
    return "Hello, World!"


@app.route("/api/finish", methods=["POST"])
def finish_squad():
    return "Hello, World!"
