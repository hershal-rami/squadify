from flask import Flask, render_template, session, request, redirect
from flask_session import Session
from flask_wtf import FlaskForm
from functools import wraps
from pymongo import MongoClient
from squadify.make_collab import Playlist, CollabBuilder
from squadify.spotify_api import SpotifyAPI
from urllib.parse import urlparse
from wtforms import StringField
import os
import spotipy
import uuid

app = Flask(__name__)

app.config["SECRET_KEY"] = os.urandom(64)
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_FILE_DIR"] = "./.flask_session/"
Session(app)

# Where Spotify auth tokens are stored
caches_folder = "./.spotify_caches/"
if not os.path.exists(caches_folder):
    os.makedirs(caches_folder)


# Get the path to this user's Spotify auth token
def spotify_cache_path():
    return caches_folder + session.get("uuid")


# Connect to running MongoDB
client = MongoClient("localhost", 27017)
db = client["squads"]["squads"]


# Apply to pages that require the user to be logged into Spotify
# Methods with this wrapper must take the parameter "spotify_api"
def authenticate(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=spotify_cache_path())
        auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)

        if not auth_manager.validate_token(cache_handler.get_cached_token()):
            # Redirect to home if not logged into Spotify
            return redirect("/")
        else:
            # "Return" SpotifyAPI object if logged into Spotify
            spotify_api = SpotifyAPI(auth_manager=auth_manager)
            kwargs["spotify_api"] = spotify_api
            return f(*args, **kwargs)

    return wrapper


# Apply to pages where Spotify login is optional, but we want to know if they
# are logged in or not
# Methods with this wrapper must take the parameters "spotify_api" and "logged_in"
def auth_optional(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=spotify_cache_path())
        auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)

        # "Return" SpotifyAPI object if logged into Spotify, None otherwise
        if auth_manager.validate_token(cache_handler.get_cached_token()):
            spotify_api = SpotifyAPI(auth_manager=auth_manager)
            kwargs["spotify_api"] = spotify_api
            kwargs["logged_in"] = True
        else:
            kwargs["spotify_api"] = None
            kwargs["logged_in"] = False
        return f(*args, **kwargs)

    return wrapper


# Ensure the user has a Flask session ID
# Apply to all pages
def ensure_session(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("uuid"):
            session["uuid"] = str(uuid.uuid4())
        return f(*args, **kwargs)

    return wrapper


# User clicked "Sign In" button
@app.route("/sign_in", methods=["GET"])
@ensure_session
def sign_in():
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=spotify_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="playlist-modify-public",  # We can edit the user's playlists
        cache_handler=cache_handler,
        show_dialog=True,
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI") + "/sign_in",  # Have Spotify send us back here
        state=request.environ.get('HTTP_REFERER')  # Send along the final destination after sign-in
    )

    if len(request.args) == 0:
        # Step 1. Go to Spotify to get authorized
        return redirect(auth_manager.get_authorize_url())
    else:
        # Step 2. Got sent back here, redirect back to wherever the user hit "Sign In" from
        auth_manager.get_access_token(request.args.get("code"))
        return redirect(request.args.get("state"))


# User clicked "Sign Out" button
@app.route("/sign_out", methods=["GET"])
@ensure_session
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(spotify_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect("/")


# Homepage
@app.route("/", methods=["GET"])
@ensure_session
@auth_optional
def homepage(spotify_api, logged_in):
    return render_template("index.html", logged_in=logged_in)


# View list of user's squads
@app.route("/squads", methods=["GET"])
@ensure_session
@authenticate
def view_squads(spotify_api):
    query = {"leader_id": spotify_api.me()["id"]}
    return render_template(
        "squads-list.html",
        logged_in=True,
        squads_list=db.find(query),
        squads_list_length=db.count_documents(query),
    )


# View a specific squad
@app.route("/squads/<uuid:squad_id>", methods=["GET"])
@ensure_session
@auth_optional
def view_squad(squad_id, spotify_api, logged_in):
    squad = db.find_one({"squad_id": str(squad_id)})
    is_leader = logged_in and spotify_api.me()["id"] == squad["leader_id"]
    return render_template(
        "squad-page.html",
        squad=squad,
        logged_in=logged_in,
        is_leader=is_leader,
        playlist_form=PlaylistForm(),
    )


class SquadForm(FlaskForm):
    squad_name = StringField()


class PlaylistForm(FlaskForm):
    user_name = StringField()
    playlist_link = StringField()


# Create new squad
@app.route("/squads/new", methods=["GET", "POST"])
@ensure_session
@authenticate
def new_squad(spotify_api):
    squad_form = SquadForm()

    # Step 2: User pressed "Form Squad" on /squads/new to get here, so we make
    # a new squad and go to the page for that squad
    if squad_form.validate_on_submit():
        squad_id = str(uuid.uuid4())
        db.insert_one(
            dict(
                squad_id=squad_id,
                squad_name=squad_form.squad_name.data,
                leader_id=spotify_api.me()["id"],
                leader_name=spotify_api.me()["display_name"],
                playlists=[],
            )
        )
        return redirect(f"/squads/{squad_id}")

    # Step 1: User pressed "Squad Up!" on the homepage, so we let the them
    # submit a squad name
    return render_template("new-squad.html", logged_in=True, squad_form=squad_form)


# Add playlist to existing squad
@app.route("/squads/<uuid:squad_id>/add", methods=["POST"])
@ensure_session
@authenticate  # TODO: User shouldn't need to log in to add a playlist
def add_playlist(squad_id, spotify_api):
    playlist_form = PlaylistForm()

    # Only try adding a playlist if the user submitted the playlist info
    if playlist_form.validate_on_submit():
        playlist_link = playlist_form.playlist_link.data

        # Alert the user if the playlist link they submit is invalid
        # TODO: Frontend dosen't use this anymore
        if spotify_api.playlist(playlist_link) == None:
            return redirect("/squads/<uuid:squad_id>/add", invalid_playlist=True)

        # Add playlist to squad
        playlist_id = urlparse(playlist_link).path.split("/")[-1]
        user_name = playlist_form.user_name.data
        db.update_one(
            {"squad_id": str(squad_id)},
            {
                "$push": {
                    "playlists": {
                        "playlist_id": playlist_id,
                        "user_name": user_name,
                    }
                }
            },
        )

    # Redirect to squad page
    return redirect(f"/squads/{squad_id}")


# Delete playlist from existing squad
@app.route("/squads/<uuid:squad_id>/delete", methods=["GET"])
@ensure_session
def delete_playlist(squad_id):
    db.update_one(
        {"squad_id": str(squad_id)},
        {
            "$pull": {
                "playlists": {
                    "playlist_id": request.args.get("playlist_id"),
                    "user_name": request.args.get("user_name"),
                }
            }
        },
    )

    # Redirect to squad page
    return redirect(f"/squads/{squad_id}")


# Create the collab and display a link to it
@app.route("/squads/<uuid:squad_id>/finish", methods=["GET"])
@ensure_session
@authenticate
def finish_squad(squad_id, spotify_api):
    squad = db.find_one({"squad_id": str(squad_id)})
    playlists = [(playlist["user_name"], playlist["playlist_id"]) for playlist in squad["playlists"]]
    playlists = [Playlist(name, spotify_api.get_tracks(id)) for name, id in playlists]
    collab = CollabBuilder(playlists).build()
    collab_id = spotify_api.publish_collab(collab, squad["squad_name"])
    return render_template(
        "finish-squad.html",
        logged_in=True,
        squad=squad,
        playlist_embed_id=collab_id,
    )
