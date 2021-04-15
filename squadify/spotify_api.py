from spotipy.oauth2 import SpotifyOAuth
import math

SCOPE = "playlist-modify-public"
TRACK_PULL_LIMIT = 100
TRACK_PUSH_LIMIT = 20


class Track:
    def __init__(self, track):
        self.title = track["name"]
        self.artists = frozenset([artist["name"] for artist in track["artists"]])
        self.id = track["id"]

    def __hash__(self):
        return hash((self.title, self.artists))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return self.title + " - " + ", ".join(self.artists)


def get_tracks(sp, playlist_link):
    num_tracks = sp.playlist(playlist_link, fields=["tracks(total)"])["tracks"]["total"]
    tracks = []
    for i in range(math.ceil(num_tracks / TRACK_PULL_LIMIT)):
        playlist_items = sp.playlist_items(playlist_link, offset=i * TRACK_PULL_LIMIT)
        tracks.extend([Track(item["track"]) for item in playlist_items["items"]])
    return tracks


def publish_squad_playlist(sp, playlist, playlist_name):
    user_id = sp.current_user()["id"]
    playlist_id = sp.user_playlist_create(user_id, playlist_name)["id"]
    tracks = [track.id for track in playlist]
    for i in range(0, len(tracks), TRACK_PUSH_LIMIT):
        tracks_subset = tracks[i : min(i + TRACK_PUSH_LIMIT, len(tracks))]
        sp.user_playlist_add_tracks(user_id, playlist_id, tracks_subset)
    return playlist_id
