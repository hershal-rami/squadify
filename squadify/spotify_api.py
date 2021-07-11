import math
from squadify.make_collab import Track
import spotipy


TRACK_PULL_LIMIT = 100  # Number of tracks the Spotify API lets you query at once
TRACK_PUSH_LIMIT = 20  # Number of tracks the Spotify API lets you add at once


# Added functionality on top of the Spotipy module
class SpotifyAPI(spotipy.Spotify):
    
    # Return a list of all the tracks from a playlist
    def get_tracks(self, playlist_id):
        num_tracks = self.playlist(playlist_id, fields=["tracks(total)"])["tracks"]["total"]
        tracks = []
        for i in range(math.ceil(num_tracks / TRACK_PULL_LIMIT)):
            playlist_items = self.playlist_items(playlist_id, offset=i * TRACK_PULL_LIMIT)
            for item in playlist_items["items"]:
                # Don't add tracks with missing data
                if item["track"] == None or item["track"]["id"] == None:
                    continue
                tracks.append(Track(item["track"]))
        return tracks


    # Make collab in leader's account and return its Spotify ID
    def publish_collab(self, collab, collab_name):
        user_id = self.current_user()["id"]
        collab_id = self.user_playlist_create(user_id, collab_name)["id"]
        tracks = [track.id for track in collab]
        for i in range(0, len(tracks), TRACK_PUSH_LIMIT):
            tracks_subset = tracks[i : min(i + TRACK_PUSH_LIMIT, len(tracks))]
            self.user_playlist_add_tracks(user_id, collab_id, tracks_subset)
        return collab_id


# Caches Spotify auth tokens in a MongoDB collection
class MongoCacheHandler(spotipy.cache_handler.CacheHandler):

    def __init__(self, collection, session_id):
        self.collection = collection
        self.session_id = session_id


    def get_cached_token(self):
        document = self.collection.find_one({"session_id": self.session_id})
        return document["token_info"] if document else None


    def save_token_to_cache(self, token_info):
        self.collection.insert_one(
            dict(
                session_id=self.session_id,
                token_info=token_info,
            )
        )


    def delete_token_from_cache(self):
        self.collection.delete_one({"session_id": self.session_id})