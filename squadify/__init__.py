from flask import Flask, render_template, session, request, redirect, abort
from flask_session import Session
from flask_wtf import FlaskForm
from functools import wraps
from pymongo import MongoClient
from spotipy.cache_handler import CacheFileHandler
from spotipy.oauth2 import SpotifyOAuth
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


class NewSquadForm(FlaskForm):
    squad_name = StringField()


class AddPlaylistForm(FlaskForm):
    user_name = StringField()
    playlist_link = StringField()


# Apply to pages where Spotify login is either required or optional
# Methods with this wrapper must take the parameters "spotify_api",
# and if required=False, "signed_in"
def authenticate(required):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            # Ensure the user has a Flask session ID
            if not session.get("uuid"):
                session["uuid"] = str(uuid.uuid4())

            cache_handler = CacheFileHandler(cache_path=spotify_cache_path())
            auth_manager = SpotifyOAuth(cache_handler=cache_handler)

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


# Signs in a user
# Route flow: <Page> -> /sign_in -> <Spotify login> -> /sign_in -> <Dest>
# <Dest> is either the dest parameter, the previous page, or / in that order
@app.get("/sign_in")
def sign_in():
    auth_manager = SpotifyOAuth(
        scope="playlist-modify-public", # Get permission to modify public playlists on behalf of the user
        cache_handler=CacheFileHandler(cache_path=spotify_cache_path()),
        show_dialog=True,
        redirect_uri=os.getenv("SPOTIPY_REDIRECT_URI") + "/sign_in", # Have Spotify send us back here after signing in
        state=request.args.get("dest", request.referrer or "/") # After being sent back here, go to this url
    )

    if not request.args.get("code"):
        # Step 1. Go to Spotify to get authorized
        return redirect(auth_manager.get_authorize_url())
    else:
        # Step 2. Got sent back here, get Spotify access token, and then redirect to final destination
        auth_manager.get_access_token(request.args.get("code"))
        return redirect(request.args.get("state"))


# Signs out a user
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
        add_playlist_form=AddPlaylistForm(),
    )


# Create a new squad
@app.route("/squads/new", methods=["GET", "POST"])
@authenticate(required=True)
def new_squad(spotify_api):
    new_squad_form = NewSquadForm()
    if not new_squad_form.validate_on_submit():
        # Step 1: User pressed "Squad Up!" on the homepage to get here, so we ask them for a squad name
        return render_template("new-squad.html", signed_in=True, new_squad_form=new_squad_form)
    else:
        # Step 2: User pressed "Create Squad" on /squads/new to get here, so we make a new squad and go to the page for that squad
        squad_id = str(uuid.uuid4())
        db.insert_one(
            dict(
                squad_id=squad_id,
                squad_name=new_squad_form.squad_name.data,
                leader_id=spotify_api.me()["id"],
                leader_name=spotify_api.me()["display_name"],
                playlists=[],
            )
        )
        return redirect(f"/squads/{squad_id}")


# Add a playlist to an existing squad
@app.post("/squads/<uuid:squad_id>/add")
def add_playlist(squad_id):
    # Add a playlist only if the user submitted the playlist info
    add_playlist_form = AddPlaylistForm()
    if add_playlist_form.validate_on_submit():
        playlist_id = urlparse(add_playlist_form.playlist_link.data).path.split("/")[-1] # TODO: What happens when this fails? Is the DB modified?
        db.update_one(
            {"squad_id": str(squad_id)},
            {
                "$push": {
                    "playlists": {
                        "playlist_id": playlist_id,
                        "user_name": add_playlist_form.user_name.data,
                    }
                }
            },
        )

    # Regardless of whether or not a playlist was added, redirect back to the squad page
    return redirect(f"/squads/{squad_id}")


# Delete a playlist from an existing squad
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


# Create a collab and display a link to it
@app.get("/squads/<uuid:squad_id>/finish")
@authenticate(required=True)
def finish_squad(squad_id, spotify_api):
    squad = db.find_one({"squad_id": str(squad_id)})
    if squad == None:
        abort(404)

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
