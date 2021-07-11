import math
from spotipy import Spotify
from .make_collab import Track


TRACK_PULL_LIMIT = 100  # Number of tracks the Spotify API lets you query at once
TRACK_PUSH_LIMIT = 20  # Number of tracks the Spotify API lets you add at once


# Added functionality on top of the Spotipy module
class SpotifyAPI(Spotify):
    
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


    def is_valid_playlist_id(self, playlist_id):
        try:
            self.playlist(playlist_id)
            return True
        except:
            return False