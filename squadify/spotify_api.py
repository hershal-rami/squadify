import math
from squadify.make_playlist import Track

TRACK_PULL_LIMIT = 100  # Number of songs the Spotify API lets you query at once
TRACK_PUSH_LIMIT = 20   # Number of songs the Spotify API lets you add at once


# Return a list of all the tracks from a playlist
def get_tracks(sp, playlist_link):
    num_tracks = sp.playlist(playlist_link, fields=["tracks(total)"])["tracks"]["total"]
    tracks = []
    for i in range(math.ceil(num_tracks / TRACK_PULL_LIMIT)):
        playlist_items = sp.playlist_items(playlist_link, offset=i*TRACK_PULL_LIMIT)
        tracks.extend([Track(item["track"]) for item in playlist_items["items"]])
    return tracks


# Make collab in leader's account and return its Spotify ID
def publish_collab(sp, collab, collab_name):
    user_id = sp.current_user()["id"]
    collab_id = sp.user_playlist_create(user_id, collab_name)["id"]
    tracks = [track.id for track in collab]
    for i in range(0, len(tracks), TRACK_PUSH_LIMIT):
        tracks_subset = tracks[i : min(i + TRACK_PUSH_LIMIT, len(tracks))]
        sp.user_playlist_add_tracks(user_id, collab_id, tracks_subset)
    return collab_id
