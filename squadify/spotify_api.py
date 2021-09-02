from spotipy import Spotify
from .make_collab import Track


TRACK_PULL_LIMIT = 100  # Number of tracks the Spotify API lets you query at once
TRACK_PUSH_LIMIT = 100  # Number of tracks the Spotify API lets you add at once
LIKED_SONGS_PULL_LIMIT = 50  # Number of liked songs the Spotify API lets you query at once
LIKED_SONGS_PLAYLIST_NAME = "User's Liked Songs"


# Added functionality on top of the Spotipy module
class SpotifyAPI(Spotify):

    # Return a list of all the tracks from a playlist
    def get_playlist_tracks(self, playlist_id):
        return self.__pull_tracks(self.playlist_items(playlist_id, limit=TRACK_PULL_LIMIT))


    # Create a new playlist contianing the given tracks to this user's account
    # Returns the ID of the new playlist
    def create_playlist_with_tracks(self, playlist_name, tracks):
        playlist_id = self.__create_playlist(playlist_name)
        self.__push_tracks(playlist_id, tracks)
        return playlist_id


    # Copy this user's Liked Songs list to a playlist
    # Returns the ID of the new playlist
    def clone_liked_songs(self):
        tracks = self.__pull_tracks(self.current_user_saved_tracks(limit=LIKED_SONGS_PULL_LIMIT))
        return self.create_playlist_with_tracks(LIKED_SONGS_PLAYLIST_NAME, tracks)


    # Pull tracks using any initial result from a function that supports pagination
    def __pull_tracks(self, result):
        # Iterate through paginated results
        items = result["items"]
        while result["next"]:
            result = self.next(result)
            items.extend(result["items"])

        # Transform items into tracks and filter out ones with missing data
        items = filter(lambda item: item["track"] and item["track"]["id"], items)
        tracks = [Track(item["track"]) for item in items]

        return tracks


    # Push the given tracks to the playlist with the given ID
    def __push_tracks(self, playlist_id, tracks):
        track_ids = [track.id for track in tracks]
        for i in range(0, len(track_ids), TRACK_PUSH_LIMIT):
            track_ids_sublist = track_ids[i : min(i + TRACK_PUSH_LIMIT, len(track_ids))]
            self.playlist_add_items(playlist_id, track_ids_sublist)


    # Add a new playlist with the given name to this user's account
    def __create_playlist(self, playlist_name):
        return self.user_playlist_create(self.current_user()["id"], playlist_name)["id"]


    # Returns whether this is the ID of a valid playlist
    def is_valid_playlist_id(self, playlist_id):
        try:
            self.playlist(playlist_id)
            return True
        except:
            return False
