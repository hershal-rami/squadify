from spotipy import Spotify
from .make_collab import Track


TRACK_PULL_LIMIT = 100  # Number of tracks the Spotify API lets you query at once
TRACK_PUSH_LIMIT = 100  # Number of tracks the Spotify API lets you add at once
TRACK_DELETE_LIMIT = 100  # Number of tracks the Spotify API lets you delete at once
PLAYLIST_PULL_LIMIT = 50  # Number of playlists the Spotify API lets you query at once
LIKED_SONGS_PULL_LIMIT = 50  # Number of liked songs the Spotify API lets you query at once
LIKED_SONGS_PLAYLIST_NAME = "Liked Songs"


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
    # If such a playlist already exists, its contents are emptied and filled with an up-to-date track list
    # Otherwise, a new playlist is created
    # Returns the ID of the playlist
    def clone_liked_songs(self):
        liked_songs = self.__pull_tracks(self.current_user_saved_tracks(limit=LIKED_SONGS_PULL_LIMIT))
        old_playlist_id = self.__get_playlist_id_from_name(LIKED_SONGS_PLAYLIST_NAME)
        if old_playlist_id:
            self.__purge_playlist(old_playlist_id)
            self.__push_tracks(old_playlist_id, liked_songs)
            return old_playlist_id
        else:
            return self.create_playlist_with_tracks(LIKED_SONGS_PLAYLIST_NAME, liked_songs)


    # Returns whether this is the ID of a valid playlist
    def is_valid_playlist_id(self, playlist_id):
        try:
            self.playlist(playlist_id)
            return True
        except:
            return False


    # Pull items using any initial result from a function that supports pagination
    def __pull_items(self, result):
        # Iterate through paginated results
        items = result["items"]
        while result["next"]:
            result = self.next(result)
            items.extend(result["items"])
        return items


    # Pull tracks using any initial result from a function that supports pagination
    def __pull_tracks(self, result):
        # Transform items into tracks and filter out ones with missing data
        items = self.__pull_items(result)
        items = filter(lambda item: item["track"] and item["track"]["id"], items)
        tracks = [Track(item["track"]) for item in items]
        return tracks


    # Given a function that takes a playlist ID and a track list of limited size,
    # batch the given track list and call the function on each batch
    def __modify_tracks(self, playlist_id, tracks, operation, operation_limit):
        track_ids = [track.id for track in tracks]
        for i in range(0, len(track_ids), operation_limit):
            track_id_batch = track_ids[i : min(i + operation_limit, len(track_ids))]
            operation(playlist_id, track_id_batch)


    # Push the given tracks to the playlist with the given ID
    def __push_tracks(self, playlist_id, tracks):
        self.__modify_tracks(playlist_id, tracks, self.playlist_add_items, TRACK_PUSH_LIMIT)


    # Delete the given tracks from the playlist with the given ID
    def __delete_tracks(self, playlist_id, tracks):
        self.__modify_tracks(playlist_id, tracks, self.playlist_remove_all_occurrences_of_items, TRACK_DELETE_LIMIT)


    # Add a new playlist with the given name to this user's account
    def __create_playlist(self, playlist_name):
        return self.user_playlist_create(self.current_user()["id"], playlist_name)["id"]


    # Empty a playlist of all its tracks
    def __purge_playlist(self, playlist_id):
        self.__delete_tracks(playlist_id, self.get_playlist_tracks(playlist_id))


    # Return the id of this user's playlist with the given name, or none if no such playlist exists
    def __get_playlist_id_from_name(self, playlist_name):
        playlists = self.__pull_items(self.current_user_playlists(limit=PLAYLIST_PULL_LIMIT))
        for playlist in playlists:
            if playlist["name"] == playlist_name:
                return playlist["id"]
        return None
