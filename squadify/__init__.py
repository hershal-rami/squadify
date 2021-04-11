__version__ = "0.1.0"

from functools import wraps
import os
from flask import Flask, render_template, session, request, redirect
from flask_session import Session
import spotipy
import uuid
from pymongo import MongoClient
from flask_wtf import FlaskForm
from wtforms import StringField

app = Flask(__name__)

app.config["SECRET_KEY"] = os.urandom(64)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_session/"
Session(app)

caches_folder = "./.spotify_caches/"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


def session_cache_path():
    return caches_folder + session.get("uuid")


client = MongoClient("localhost", 27017)
db = client["squads"]["squads"]


def authenticate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        cache_handler = spotipy.cache_handler.CacheFileHandler(
            cache_path=session_cache_path()
        )
        auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)
        if not auth_manager.validate_token(cache_handler.get_cached_token()):
            return redirect("/")
        else:
            sp = spotipy.Spotify(auth_manager=auth_manager)
            kwargs["sp"] = sp
            return f(*args, **kwargs)

    return wrapper

def auth_optional(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        cache_handler = spotipy.cache_handler.CacheFileHandler(
            cache_path=session_cache_path()
        )
        auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)

        kwargs["sp"] = None
        if auth_manager.validate_token(cache_handler.get_cached_token()):
            sp = spotipy.Spotify(auth_manager=auth_manager)
            kwargs["sp"] = sp
        return f(*args, **kwargs)

    return wrapper


@app.route("/")
def homepage():
    if not session.get("uuid"):
        # Step 1. Visitor is unknown, give random ID
        session["uuid"] = str(uuid.uuid4())

    cache_handler = spotipy.cache_handler.CacheFileHandler(
        cache_path=session_cache_path()
    )
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="playlist-modify-public",
        cache_handler=cache_handler,
        show_dialog=True,
        redirect_uri="http://localhost:5000",
    )

    if request.args.get("code"):
        # Step 3. Being redirected from Spotify auth page
        auth_manager.get_access_token(request.args.get("code"))
        return redirect("/")

    if not auth_manager.validate_token(cache_handler.get_cached_token()):
        # Step 2. Display sign in link when no token
        auth_url = auth_manager.get_authorize_url()
        return render_template("index.html", logged_in=False, auth_url=auth_url)

    # Step 4. Signed in, display data
    return render_template("index.html", logged_in=True)


@app.route("/sign_out")
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(session_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect("/")


@app.route("/about")
@auth_optional
def view_about(sp):
    return render_template("about.html", logged_in=(sp != None))


# Viewing existing squads
@app.route("/squads")
@authenticate
def view_squads(sp):
    return render_template(
        "squads.html", logged_in=True, squads_list=db.find({"user": sp.me()["id"]})
    )


# Viewing specific squad's playlists
@app.route("/squads/<uuid:squad_id>")
@auth_optional
def view_squad(squad_id, sp):
    #TODO Use user's name, not just ID
    squad = db.find_one({"squad_id": str(squad_id)})
    leader = (sp != None) and (sp.me()["id"] == squad["user"])
    return render_template(
        "squad.html", logged_in=True, squad=squad, playlist_form=PlaylistForm(),
        leader=leader
    )


class SquadForm(FlaskForm):
    squad_name = StringField("Squad Name:")

class PlaylistForm(FlaskForm):
    user_name = StringField("User Name:")
    playlist_link = StringField("Playlist Link:")


# Create new squad
@app.route("/squads/new", methods=["GET", "POST"])
@authenticate
def new_squad(sp):
    squad_form = SquadForm()

    if squad_form.validate_on_submit():
        squad_name = squad_form.squad_name.data
        # generate an id, get user id, make playlists empty
        squad_id = str(uuid.uuid4())
        db.insert_one(
            dict(
                user=sp.me()["id"],
                squad_name=squad_name,
                squad_id=squad_id,
                playlists=[],
            )
        )
        return redirect(f"/squads/{squad_id}")

    return render_template("add-squad.html", logged_in=True, squad_form=squad_form)


# Add playlist to existing squad
@app.route("/squads/<uuid:squad_id>/add", methods=["GET", "POST"])
@authenticate
def add_to_squad(squad_id, sp):
    playlist_form = PlaylistForm()

    if playlist_form.validate_on_submit():
        playlist_link = playlist_form.playlist_link.data
        user_name = playlist_form.user_name.data
        db.update_one(
            {"squad_id": str(squad_id)},
            {"$push": {"playlists":
            {"playlist_link": playlist_link,
            "user_name": user_name}}})
    
    return redirect(f"/squads/{squad_id}")


# Public new playlist for squad
@app.route("/squads/<uuid:squad_id>/finish", methods=["GET", "POST"])
@authenticate
def finish_squad(squad_id, sp):
    squad = db.find_one({"squad_id": str(squad_id)})
    playlists = []
