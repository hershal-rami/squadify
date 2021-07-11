import uuid
from flask import session, abort
from pymongo import MongoClient
from spotipy.cache_handler import CacheHandler
from werkzeug.routing import BaseConverter
from . import db


client = MongoClient("localhost", 27017)
db = client["squadify"]
squads_collection = db["squads"]
spotify_token_collection = db["tokens"]


def get_user_squad_list(spotify_api):
    return list(squads_collection.find({"leader_id": spotify_api.me()["id"]}))


def insert_squad(squad_id, squad_name, spotify_api):
    squads_collection.insert_one(
        dict(
            squad_id=squad_id,
            squad_name=squad_name,
            leader_id=spotify_api.me()["id"],
            leader_name=spotify_api.me()["display_name"],
            playlists=[],
        )
    )


def add_playlist_to_squad(squad_id, playlist_id, user_name):
    squads_collection.update_one(
        {"squad_id": squad_id},
        {
            "$push": {
                "playlists": {
                    "playlist_id": playlist_id,
                    "user_name": user_name,
                }
            }
        },
    )


def delete_playlist_from_squad(squad_id, playlist_id, user_name):
    squads_collection.update_one(
        {"squad_id": squad_id},
        {
            "$pull": {
                "playlists": {
                    "playlist_id": playlist_id,
                    "user_name": user_name,
                }
            }
        },
    )


# Get a CacheHandler that stores this user's Spotify auth token
def spotify_cache_handler():
    session["uuid"] = session.get("uuid", str(uuid.uuid4())) # Ensure the user has a Flask session ID
    return MongoCacheHandler(session["uuid"])


# Caches Spotify auth tokens in a MongoDB collection
class MongoCacheHandler(CacheHandler):

    def __init__(self, session_id):
        self.session_id = session_id

    def get_cached_token(self):
        document = spotify_token_collection.find_one({"session_id": self.session_id})
        return document["token_info"] if document else None

    def save_token_to_cache(self, token_info):
        spotify_token_collection.insert_one(
            dict(
                session_id=self.session_id,
                token_info=token_info,
            )
        )

    def delete_token_from_cache(self):
        # Should only need to delete one, but duplicate tokens have been found
        # during development
        spotify_token_collection.delete_many({"session_id": self.session_id})


# Fetches a squad from a squad_id, or returns a 404 if it doesn't exist
class SquadConverter(BaseConverter):

    def to_python(self, squad_id):
        squad = squads_collection.find_one({"squad_id": squad_id})
        if squad == None:
            abort(404)
        return squad

    def to_url(self, squad):
        return squad["squad_id"]
