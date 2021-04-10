__version__ = "0.1.0"

from flask import Flask
from flask import render_template
from flask_mongoengine import MongoEngine
import mongoengine as me

app = Flask(__name__)
logged_in = False

app.config['MONGODB_SETTINGS'] = {
    'db': 'squads',
    'host': 'localhost',
    'port': 27017
}
db = MongoEngine()
db.init_app(app)

class Squad(me.Document):
    name = me.StringField()
    playlists = me.ListField()

@app.route("/")
def homepage():
    return render_template("index.html", logged_in=logged_in)

@app.route("/about")
def view_about():
    return render_template("about.html", logged_in=logged_in)

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