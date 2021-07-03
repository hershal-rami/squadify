import random
from collections import Counter

# Arbitrary max collab size we impose
MAX_COLLAB_SIZE = 50

# Used to ensure each member gets at least m tracks in the collab,
# where m = MAX_COLLAB_SIZE / num_members * MIN_SHARE_FACTOR
MIN_SHARE_FACTOR = 0.5

# Only add a track to the collab if it has at least this frequency
MIN_FREQUENCY = 2


# Points to a previous and next track
class Node:
    def __init__(self):
        self.prev = None
        self.next = None


# A single track
class Track:
    def __init__(self, track):
        self.title = track["name"]
        self.artists = frozenset([artist["name"] for artist in track["artists"]])
        self.id = track["id"]
        self.members = {None: Node()}  # Dummy member that owns all tracks

    # Record that this track is owned by another member
    def add_member(self, member):
        self.members[member] = Node()

    # Return the number of members that own this track
    def frequency(self):
        return len(self.members) - 1  # Don't count the dummy

    # Get the next track owned by a member after this one
    def get_next(self, member):
        return self.members[member].next

    # Get the previous track owned by a member before this one
    def get_prev(self, member):
        return self.members[member].prev

    # Set the next track owned by a member after this one
    def set_next(self, member, track):
        self.members[member].next = track

    # Set the previous track owned by a member before this one
    def set_prev(self, member, track):
        self.members[member].prev = track

    def __hash__(self):
        return hash((self.title, self.artists))

    def __eq__(self, other):
        return hash(self) == hash(other)

    def __str__(self):
        return self.title + " - " + ", ".join(self.artists)


# A list of tracks from a playlist and the member who provided the playlist
class Playlist:
    def __init__(self, member, tracks):
        self.member = member
        self.tracks = tracks


class CollabBuilder:
    def __init__(self, playlists):
        # Dictionary mapping a member name to a playlist of tracks
        self.playlists = playlists

        # The collaborative playlist we're building
        self.collab = []

        # All the tracks from all the playlists
        self.tracks = []

        # Names of all the squad members
        self.members = set({None})

        # Number of unadded tracks at each frequency
        self.num_tracks_left_for_freq = None

        # How many tracks each member has added
        self.num_tracks_added_for_member = None

        # Each member's most popular track
        self.most_popular_track_of_member = None

    # Return a list of all tracks from the playlists (sorted from most to least
    # popular), list of all the members, and a dictionary containing the number of
    # tracks at each frequency level. Each track is also labeled with which members
    # own it.
    def __create_track_list(self):
        # For each track, create a set of the members who own it
        tracks_to_members = dict()
        for playlist in self.playlists:
            self.members.add(playlist.member)
            for track in playlist.tracks:
                members_of_track = tracks_to_members.setdefault(track, set())
                members_of_track.add(playlist.member)
                tracks_to_members[track] = members_of_track

        # Move those members from the dictionary into each track object
        # and create the track list
        for track, members_of_track in tracks_to_members.items():
            for member in members_of_track:
                track.add_member(member)
            self.tracks.append(track)

        # Eliminate tracks below the minimum frequency
        self.tracks = list(filter(lambda track: track.frequency() >= MIN_FREQUENCY, self.tracks))

        # Get a slightly different collab each time it's compiled
        random.shuffle(self.tracks)

        # Sort the tracks by frequency (number of members owning it)
        self.tracks.sort(key=Track.frequency, reverse=True)

        self.num_tracks_left_for_freq = Counter(map(Track.frequency, self.tracks))
        self.num_tracks_added_for_member = {member: 0 for member in self.members}

    # Have each track point to the previous and next one in the list of all tracks.
    # Also, for each track, for each member, point to the previous/next track in the
    # list that this member owns.
    def __populate_linkedness(self):
        # Stores the previous track owned by each member
        prev_track_of_member = {member: None for member in self.members}

        # Stores the track at the top of the list for each member
        self.most_popular_track_of_member = {member: None for member in self.members}

        # Link each track to the previous track owned by each member
        for track in self.tracks:
            for member in track.members:

                # Set this track's previous
                track.set_prev(member, prev_track_of_member[member])

                if prev_track_of_member[member] is None:
                    # This is the first track we've seen from this member
                    self.most_popular_track_of_member[member] = track
                else:
                    # Set the previous track's next
                    prev_track_of_member[member].set_next(member, track)

                # Update the previous track
                prev_track_of_member[member] = track

    # Add track to the collab and remove it from the track list
    def __consume_track(self, track):
        # Add the track to the collab
        self.collab.append(track)

        # This track's frequency now has one less track
        self.num_tracks_left_for_freq[track.frequency()] -= 1

        # It might have no tracks left now; if so, remove it from the dict
        self.num_tracks_left_for_freq = +self.num_tracks_left_for_freq

        # Update linkedness for each member
        for member in track.members:

            # This member just got a track in the collab
            self.num_tracks_added_for_member[member] += 1

            # Essentially removing a node of a linked list
            if track.get_prev(member) is None:
                # The track being removed was this member's most popular track
                # Removing the head of a linked list
                self.most_popular_track_of_member[member] = track.get_next(member)
            else:
                # Removing a node from the middle of a linked list
                track.get_prev(member).set_next(member, track.get_next(member))
            # Either way, update previous of next, unless there is no next
            if track.get_next(member) is not None:
                track.get_next(member).set_prev(member, track.get_prev(member))

    # Add the given member's most popular track to the collab and remove it from the
    # track list
    # Return true if successful, false if this member has no tracks left
    def __consume_most_popular_track_of_member(self, member):
        # This member has no more tracks
        if self.most_popular_track_of_member[member] == None:
            return False

        self.__consume_track(self.most_popular_track_of_member[member])

        return True

    # Add all tracks of a given freqency to the collab and remove them all from the
    # track list
    # Return true if the entire freqency could be added, false if doing so exceeds
    # the max collab size
    def __consume_highest_frequency(self):
        # No tracks are left
        if self.__no_more_tracks():
            return False

        # Number of tracks at the highest frequency level remaining
        count_of_highest_freq = self.num_tracks_left_for_freq[self.__get_highest_frequency()]

        # Adding all of the tracks would put us over the limit
        if count_of_highest_freq + len(self.collab) > MAX_COLLAB_SIZE:
            return False

        # Consume all tracks in the highest frequency level
        for _ in range(count_of_highest_freq):
            self.__consume_track(self.__get_most_popular_track())

        return True

    # Return true if all available tracks have been added to the collab already
    def __no_more_tracks(self):
        return len(self.num_tracks_left_for_freq) == 0

    # Return the track at the top of the track list that hasn't been added yet
    def __get_most_popular_track(self):
        return self.most_popular_track_of_member[None]

    # Return the highest frequency that still has tracks remaining to be added
    def __get_highest_frequency(self):
        return self.__get_most_popular_track().frequency()

    # Return the number of squad members
    # Minus one to exclude the dummy
    def __get_number_of_members(self):
        return len(self.members) - 1

    # Make sure each member reaches a minimum threshold of tracks in the collab
    # Give up on a member if they don't have enough tracks to reach the threshold
    def __give_members_minimum_share(self):
        min_tracks_per_member = int(MAX_COLLAB_SIZE / self.__get_number_of_members() * MIN_SHARE_FACTOR)
        for member in self.members:
            num_tracks_needed = min_tracks_per_member - self.num_tracks_added_for_member[member]
            for i in range(num_tracks_needed):
                if not self.__consume_most_popular_track_of_member(member):
                    break  # This member has no songs left

    # Consume the highest frequencies until one frequency can't be added entirely
    # without exceeding the max collab size or no tracks are left
    def __add_all_of_highest_frequencies(self):
        while self.__consume_highest_frequency():
            pass

    # Fill the rest of the playlist with tracks from the highest frequency level
    # remaining, prioritizing the tracks of members with the least songs added
    def __add_some_of_last_frequency(self):
        # No tracks are left
        if self.__no_more_tracks():
            return False

        # The highest frequency with tracks remaining
        last_frequency = self.__get_highest_frequency()

        # Filter for only members with tracks at the highest frequency
        filtered_members = self.members.copy()

        # Iterate until the collab has reached its max size
        while len(self.collab) < MAX_COLLAB_SIZE:

            # Find the member with the fewest tracks added to the collab
            filtered_track_counts = {member: self.num_tracks_added_for_member[member] for member in filtered_members}
            least_popular_member = min(filtered_track_counts, key=filtered_track_counts.get)

            # Get that member's most popular track
            track = self.most_popular_track_of_member[least_popular_member]

            # If that member has no tracks left or the track is not in the
            # highest frequency level, remove this member from consideration
            if track == None or track.frequency() < last_frequency:
                filtered_members.remove(least_popular_member)
                continue

            # Otherwise, consume the track
            self.__consume_track(track)

    # Make a collaborative playlist (collab) out of the playlists of each squad member
    def build(self):
        self.__create_track_list()
        self.__populate_linkedness()
        self.__give_members_minimum_share()
        self.__add_all_of_highest_frequencies()
        self.__add_some_of_last_frequency()

        return self.collab
