import os
import uuid
from flask import render_template, request, redirect
from functools import wraps
from urllib.parse import urlparse
from spotipy.oauth2 import SpotifyOAuth
from .spotify_api import SpotifyAPI
from .make_collab import Playlist, CollabBuilder
from .forms import *
from . import app, database


# Apply to pages where it is either optional or required that the user be signed in
# Routes with this wrapper must take the parameters "spotify_api", and if required=False, "signed_in"
def authenticate(required):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            cache_handler = database.spotify_cache_handler()
            auth_manager = SpotifyOAuth(cache_handler=cache_handler)

            if auth_manager.validate_token(cache_handler.get_cached_token()):
                # User is not signed in
                spotify_api = SpotifyAPI(auth_manager=auth_manager)
                kwargs["spotify_api"] = spotify_api
                if not required:
                    kwargs["signed_in"] = True
            else:
                # User is not signed in
                if required:
                    # Must be signed in to be here, send user back to home
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
        cache_handler=database.spotify_cache_handler(),
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
    database.spotify_cache_handler().delete_token_from_cache()
    print("sign out")
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
    return render_template(
        "squads-list.html",
        signed_in=True,
        squads_list=database.get_user_squad_list(spotify_api),
    )


# View a specific squad
@app.get("/squads/<squad:squad>")
@authenticate(required=False)
def view_squad(spotify_api, signed_in, squad):
    return render_template(
        "squad-page.html",
        squad=squad,
        signed_in=signed_in,
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
        database.insert_squad(squad_id, new_squad_form.squad_name.data, spotify_api)
        return redirect(f"/squads/{squad_id}")


# Add a playlist to an existing squad
# Note: We know that playlist_link is a valid URL via form validation, but we
# don't know if the playlist_id we get out of it points to a valid playlist
# until it's time to compile the collab
@app.post("/squads/<squad:squad>/add_playlist")
def add_playlist(squad):
    add_playlist_form = AddPlaylistForm()

    # Add a playlist only if the user submitted the playlist info
    if add_playlist_form.validate_on_submit():
        playlist_id = urlparse(add_playlist_form.playlist_link.data).path.split("/")[-1]
        database.add_playlist_to_squad(squad["squad_id"], playlist_id, add_playlist_form.user_name.data)

    # Regardless of whether or not a playlist was added, redirect back to the squad page
    return redirect(f"/squads/{squad['squad_id']}")


# Delete a playlist from an existing squad
@app.get("/squads/<squad:squad>/delete_playlist")
def delete_playlist(squad):
    database.delete_playlist_from_squad(squad["squad_id"], request.args.get("playlist_id"), request.args.get("user_name"))

    # Redirect to squad page
    return redirect(f"/squads/{squad['squad_id']}")


# Create a collab and display a link to it
@app.get("/squads/<squad:squad>/compile")
@authenticate(required=True)
def compile_squad(spotify_api, squad):
    # Transform playlists list and filter out invalid playlist ids
    playlists = [(playlist["user_name"], playlist["playlist_id"]) for playlist in squad["playlists"]]
    playlists = filter(lambda playlist: spotify_api.is_valid_playlist_id(playlist[1]), playlists)
    playlists = [Playlist(name, spotify_api.get_tracks(id)) for name, id in playlists]

    # Do nothing if the squad has no valid playlists
    if len(playlists) == 0:
        return redirect(f"/squads/{squad['squad_id']}")

    # Build collab
    collab = CollabBuilder(playlists).build()
    collab_id = spotify_api.publish_collab(collab, squad["squad_name"])

    return render_template(
        "compile-squad.html",
        signed_in=True,
        squad=squad,
        playlist_embed_id=collab_id,
    )
