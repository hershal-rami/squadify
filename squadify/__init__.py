from flask import Flask, render_template, session, request, redirect, abort
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


class SquadForm(FlaskForm):
    squad_name = StringField()


class PlaylistForm(FlaskForm):
    user_name = StringField()
    playlist_link = StringField()


# Apply to pages where Spotify login is either required or optional
# Methods with this wrapper must take the parameters "spotify_api" and, if
# required=False, "signed_in"
def authenticate(required):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Ensure the user has a Flask session ID
            if not session.get("uuid"):
                session["uuid"] = str(uuid.uuid4())

            cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=spotify_cache_path())
            auth_manager = spotipy.oauth2.SpotifyOAuth(cache_handler=cache_handler)

            if auth_manager.validate_token(cache_handler.get_cached_token()):
                # User is logged into Spotify
                spotify_api = SpotifyAPI(auth_manager=auth_manager)
                kwargs["spotify_api"] = spotify_api
                if not required:
                    kwargs["signed_in"] = True
            else:
                # User is not logged into Spotify
                if required:
                    # Must be logged in to be here, send user back to home
                    return redirect("/")
                kwargs["spotify_api"] = None
                kwargs["signed_in"] = False

            return f(*args, **kwargs)
        return wrapper
    return decorator


# User clicked "Sign In" button
@app.get("/sign_in")
def sign_in():
    cache_handler = spotipy.cache_handler.CacheFileHandler(cache_path=spotify_cache_path())
    auth_manager = spotipy.oauth2.SpotifyOAuth(
        scope="playlist-modify-public",  # We can edit the user's playlists
        cache_handler=cache_handler,
        show_dialog=True,
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI") + "/sign_in",  # Have Spotify send us back here
        state=request.args.get("dest", request.environ.get('HTTP_REFERER'))  # Final destination after sign-in
    )

    if not request.args.get("code"):
        # Step 1. Go to Spotify to get authorized
        return redirect(auth_manager.get_authorize_url())
    else:
        # Step 2. Got sent back here, redirect to final destination
        auth_manager.get_access_token(request.args.get("code"))
        return redirect(request.args.get("state"))


# User clicked "Sign Out" button
@app.get("/sign_out")
def sign_out():
    try:
        # Remove the CACHE file (.cache-test) so that a new user can authorize.
        os.remove(spotify_cache_path())
        session.clear()
    except OSError as e:
        print("Error: %s - %s." % (e.filename, e.strerror))
    return redirect("/")


# Homepage
@app.get("/")
@authenticate(required=False)
def homepage(spotify_api, signed_in):
    return render_template("index.html", signed_in=signed_in)


# View list of user's squads
@app.get("/squads")
@authenticate(required=True)
def view_squads(spotify_api):
    query = {"leader_id": spotify_api.me()["id"]}
    return render_template(
        "squads-list.html",
        signed_in=True,
        squads_list=db.find(query),
        squads_list_length=db.count_documents(query),
    )


# View a specific squad
@app.get("/squads/<uuid:squad_id>")
@authenticate(required=False)
def view_squad(squad_id, spotify_api, signed_in):
    squad = db.find_one({"squad_id": str(squad_id)})
    if squad == None:
        abort(404)
    is_leader = signed_in and spotify_api.me()["id"] == squad["leader_id"]
    return render_template(
        "squad-page.html",
        squad=squad,
        signed_in=signed_in,
        is_leader=is_leader,
        playlist_form=PlaylistForm(),
    )


# Create new squad
@app.route("/squads/new", methods=["GET", "POST"])
@authenticate(required=True)
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
    return render_template("new-squad.html", signed_in=True, squad_form=squad_form)


# Add playlist to existing squad
@app.post("/squads/<uuid:squad_id>/add")
def add_playlist(squad_id):
    playlist_form = PlaylistForm()

    # Only try adding a playlist if the user submitted the playlist info
    if playlist_form.validate_on_submit():
        playlist_link = playlist_form.playlist_link.data

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
@app.get("/squads/<uuid:squad_id>/delete")
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
@app.get("/squads/<uuid:squad_id>/finish")
@authenticate(required=True)
def finish_squad(squad_id, spotify_api):
    squad = db.find_one({"squad_id": str(squad_id)})
    playlists = [(playlist["user_name"], playlist["playlist_id"]) for playlist in squad["playlists"]]
    playlists = [Playlist(name, spotify_api.get_tracks(id)) for name, id in playlists]
    collab = CollabBuilder(playlists).build()
    collab_id = spotify_api.publish_collab(collab, squad["squad_name"])
    return render_template(
        "finish-squad.html",
        signed_in=True,
        squad=squad,
        playlist_embed_id=collab_id,
    )
