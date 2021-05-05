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
        self.members = {None: Node()}   # Dummy member that owns all tracks
    
    # Record that this track is owned by another member
    def add_member(self, member):
        self.members[member] = Node()
    
    # Return the number of members that own this track
    def frequency(self):
        return len(self.members) - 1    # Don't count the dummy
    
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


# Return a list of all tracks from the playlists (sorted from most to least
# popular), list of all the members, and a dictionary containing the number of
# tracks at each frequency level. Each track is also labeled with which members
# own it.
def create_track_list(playlists):
    global tracks                       # All the tracks from all the playlists
    global members                      # Names of all the squad members
    global num_tracks_left_for_freq     # Number of unadded tracks at each frequency
    global num_tracks_added_for_member  # How many tracks each member has added

    tracks = []
    members = set({None})
    tracks_to_members = dict()

    # For each track, create a set of the members who own it
    for playlist in playlists:
        members.add(playlist.member)
        for track in playlist.tracks:
            members_of_track = tracks_to_members.setdefault(track, set())
            members_of_track.add(playlist.member)
            tracks_to_members[track] = members_of_track
    
    # Move those members from the dictionary into each track object
    # and create the track list
    for track, members_of_track in tracks_to_members.items():
        for member in members_of_track:
            track.add_member(member)
        tracks.append(track)
    
    # Eliminate tracks below the minimum frequency
    tracks = list(filter(lambda track: track.frequency() >= MIN_FREQUENCY, tracks))

    # Get a slightly different collab each time it's compiled
    random.shuffle(tracks)

    # Sort the tracks by frequency (number of members owning it)
    tracks.sort(key=Track.frequency, reverse=True)

    num_tracks_left_for_freq = Counter(map(Track.frequency, tracks))
    num_tracks_added_for_member = {member : 0 for member in members}


# Have each track point to the previous and next one in the list of all tracks.
# Also, for each track, for each member, point to the previous/next track in the
# list that this member owns.
def populate_linkedness():
    global tracks
    global members
    global most_popular_track_of_member

    # Stores the previous track owned by each member
    prev_track_of_member = {member: None for member in members}

    # Stores the track at the top of the list for each member
    most_popular_track_of_member = {member: None for member in members}

    # Link each track to the previous track owned by each member
    for track in tracks:
        for member in track.members:
            
            # Set this track's previous
            track.set_prev(member, prev_track_of_member[member])

            if prev_track_of_member[member] is None:
                # This is the first track we've seen from this member
                most_popular_track_of_member[member] = track
            else:
                # Set the previous track's next
                prev_track_of_member[member].set_next(member, track)
            
            # Update the previous track
            prev_track_of_member[member] = track


# Add track to the collab and remove it from the track list
def consume_track(track):
    global collab
    global num_tracks_left_for_freq
    global num_tracks_added_for_member
    global most_popular_track_of_member

    # Add the track to the collab
    collab.append(track)

    # This track's frequency now has one less track
    num_tracks_left_for_freq[track.frequency()] -= 1

    # It might have no tracks left now; if so, remove it from the dict
    num_tracks_left_for_freq = +num_tracks_left_for_freq

    # Update linkedness for each member
    for member in track.members:
        
        # This member just got a track in the collab
        num_tracks_added_for_member[member] += 1

        # Essentially removing a node of a linked list
        if track.get_prev(member) is None:
            # The track being removed was this member's most popular track
            # Removing the head of a linked list
            most_popular_track_of_member[member] = track.get_next(member)
        else:
            # Removing a node from the middle of a linked list
            track.get_prev(member).set_next(member, track.get_next(member))
        # Either way, update previous of next, unless there is no next
        if track.get_next(member) is not None:
            track.get_next(member).set_prev(member, track.get_prev(member))


# Add the given member's most popular track to the collab and remove it from the
# track list
# Return true if successful, false if this member has no tracks left
def consume_most_popular_track_of_member(member):
    global most_popular_track_of_member

    # This member has no more tracks
    if most_popular_track_of_member[member] == None:
        return False

    consume_track(most_popular_track_of_member[member])
    
    return True


# Add all tracks of a given freqency to the collab and remove them all from the
# track list
# Return true if the entire freqency could be added, false if doing so exceeds
# the max collab size
def consume_highest_frequency():
    global num_tracks_left_for_freq
    global collab

    # No tracks are left
    if len(num_tracks_left_for_freq) == 0:
        return False
    
    # Number of tracks at the highest frequency level remaining
    count_of_highest_freq = \
        sorted(num_tracks_left_for_freq.items(), key=lambda item: item[0])[-1][1]
    
    # Adding all of the tracks would put us over the limit
    if count_of_highest_freq + len(collab) > MAX_COLLAB_SIZE:
        return False
    
    # Consume all tracks in the highest frequency level
    for _ in range(count_of_highest_freq):
        consume_track(get_most_popular_track())
    
    return True


# Return the track at the top of the track list that hasn't been added yet
def get_most_popular_track():
    global most_popular_track_of_member

    return most_popular_track_of_member[None]


# Return the name of the member with the fewest tracks currently in the collab
def get_member_with_fewest_tracks_added():
    global num_tracks_added_for_member

    return min(num_tracks_added_for_member, key=num_tracks_added_for_member.get)


# Return the number of squad members
# Minus one to exclude the dummy
def get_number_of_members():
    global members

    return len(members) - 1


# Make sure each member reaches a minimum threshold of tracks in the collab
# Give up on a member if they don't have enough tracks to reach the threshold
def give_members_minimum_share():
    global tracks
    global members
    global num_tracks_added_for_member

    min_tracks_per_member = int(MAX_COLLAB_SIZE / get_number_of_members() * MIN_SHARE_FACTOR)
    for member in members:
        num_tracks_needed = min_tracks_per_member - num_tracks_added_for_member[member]
        for i in range(num_tracks_needed):
            if not consume_most_popular_track_of_member(member):
                break   # This member has no songs left


# Consume the highest frequencies until one frequency can't be added entirely
# without exceeding the max collab size or no tracks are left
def add_all_of_highest_frequencies():
    while (consume_highest_frequency()):
        pass


# Fill the rest of the playlist by repeatedly taking the most popular track of
# the member with the least tracks added
def fill_collab_with_unpopular_members():
    global collab
    global num_tracks_left_for_freq
    global most_popular_track_of_member

    # Add to the collab size max or the number of tracks left, whichever is smaller
    num_songs_to_add = min(MAX_COLLAB_SIZE - len(collab), sum(num_tracks_left_for_freq.values()))
    for _ in range(num_songs_to_add):
        consume_track(most_popular_track_of_member[get_member_with_fewest_tracks_added()])


# Make a collaborative playlist out of the playlists of each squad member
def make_collab(playlists):
    global collab
    collab = []

    create_track_list(playlists)
    populate_linkedness()
    give_members_minimum_share()
    add_all_of_highest_frequencies()
    fill_collab_with_unpopular_members()

    return collab