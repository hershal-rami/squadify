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
from werkzeug.routing import BaseConverter
from wtforms import StringField, validators
from wtforms.fields.html5 import URLField
import os
import uuid


# Connect to running MongoDB
client = MongoClient("localhost", 27017)
db = client["squads"]["squads"]


# Fetches a squad from a squad_id, or returns a 404 if it doesn't exist
class SquadConverter(BaseConverter):
    def to_python(self, squad_id):
        squad = db.find_one({"squad_id": squad_id})
        if squad == None:
            abort(404)
        return squad

    def to_url(self, squad):
        return squad["squad_id"]


app = Flask(__name__)

app.url_map.converters["squad"] = SquadConverter

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


class NewSquadForm(FlaskForm):
    squad_name = StringField(validators=[validators.length(max=40), validators.input_required()])


class AddPlaylistForm(FlaskForm):
    user_name = StringField(validators=[validators.length(max=40), validators.input_required()])
    playlist_link = URLField(validators=[validators.length(max=200), validators.input_required()])


# Apply to pages where Spotify login is either required or optional
# Routes with this wrapper must take the parameters "spotify_api", and if required=False, "signed_in"
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
@app.get("/squads/<squad:squad>")
@authenticate(required=False)
def view_squad(spotify_api, signed_in, squad):
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
        # Step 1: Ask user for a squad name
        return render_template("new-squad.html", signed_in=True, new_squad_form=new_squad_form)
    else:
        # Step 2: User pressed "Create Squad", so we make a new squad and go to the squad page for it
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
@app.post("/squads/<squad:squad>/add")
def add_playlist(squad):
    # Add a playlist only if the user submitted the playlist info
    add_playlist_form = AddPlaylistForm()
    if add_playlist_form.validate_on_submit():
        # We don't care about playlist_id validity, or if it's even a url here
        # We have no idea if a url is valid or not until it's time to compile the collab
        playlist_id = urlparse(add_playlist_form.playlist_link.data).path.split("/")[-1]
        db.update_one(
            {"squad_id": squad["squad_id"]},
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
    return redirect(f"/squads/{squad['squad_id']}")


# Delete a playlist from an existing squad
@app.get("/squads/<squad:squad>/delete")
def delete_playlist(squad):
    db.update_one(
        {"squad_id": squad["squad_id"]},
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
    return redirect(f"/squads/{squad['squad_id']}")


# Create a collab and display a link to it
@app.get("/squads/<squad:squad>/finish")
@authenticate(required=True)
def finish_squad(spotify_api, squad):
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
