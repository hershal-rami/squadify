import math
from squadify.make_playlist import Track

TRACK_PULL_LIMIT = 100  # Number of tracks the Spotify API lets you query at once
TRACK_PUSH_LIMIT = 20  # Number of tracks the Spotify API lets you add at once


# Return a list of all the tracks from a playlist
def get_tracks(spotify_api, playlist_link):
    num_tracks = spotify_api.playlist(playlist_link, fields=["tracks(total)"])[
        "tracks"
    ]["total"]
    tracks = []
    for i in range(math.ceil(num_tracks / TRACK_PULL_LIMIT)):
        playlist_items = spotify_api.playlist_items(
            playlist_link, offset=i * TRACK_PULL_LIMIT
        )
        for item in playlist_items["items"]:
            # Don't add tracks with missing data
            if item["track"] == None or item["track"]["id"] == None:
                continue
            tracks.append(Track(item["track"]))
    return tracks


# Make collab in leader's account and return its Spotify ID
def publish_collab(spotify_api, collab, collab_name):
    user_id = spotify_api.current_user()["id"]
    collab_id = spotify_api.user_playlist_create(user_id, collab_name)["id"]
    tracks = [track.id for track in collab]
    for i in range(0, len(tracks), TRACK_PUSH_LIMIT):
        tracks_subset = tracks[i : min(i + TRACK_PUSH_LIMIT, len(tracks))]
        spotify_api.user_playlist_add_tracks(user_id, collab_id, tracks_subset)
    return collab_id
