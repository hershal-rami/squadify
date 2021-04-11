import random

class Member:
    def __init__(self, name, member_num):
        self.name = name
        self.count = 0
        self.songs = [[] for _ in range(member_num + 1)]

class Playlist:
    def __init__(self, name, tracks):
        self.name = name
        self.tracks = tracks

def playlists_to_members(playlists):
    # Compute track freqencies
    tracks = {}
    for playlist in playlists:
        for track in playlist.tracks:
            if track in tracks:
                tracks[track][0] += 1
                tracks[track][1].append(playlist.name)
            else:
                tracks[track] = [1, [playlist.name]]

    # Map the member names to members and populate their songs list
    members = {
        playlist.name: Member(playlist.name, len(playlists)) for playlist in playlists
    }
    for track, values in tracks.items():
        level, listeners = values
        for listener in listeners:
            members[listener].songs[level].append(track)

    # Convert dictionary to list
    members = list(members.values())

    # Shuffle songs and members
    for member in members:
        for level in member.songs:
            random.shuffle(level)
    random.shuffle(members)

    return members

# checks if threshold is met for all members
def thresh_met(members, thresh):
    ret = True
    for member in members:
        if member.count < thresh:
            ret = False
    return ret

# returns the member with smallest count
def smallest_count(members):
    smallest_member = members[0]
    smallest_count = members[0].count
    for member in members:
        if member.count < smallest_count:
            smallest_member = member
            smallest_count = member.count
    return smallest_member

# removes a song from all members, increments count
def remove(song, level, members, final_playlist):
    rem_list = []
    final_playlist.append(song)
    for i, member in enumerate(members, start=0):
        if len(member.songs) > level:
            if song in member.songs[level]:
                member.count += 1
                member.songs[level].remove(song)

                # removes extra levels from at song lists
                highest_level = len(member.songs) - 1
                while len(member.songs[highest_level]) == 0 and highest_level >= 2:
                    member.songs.pop()
                    highest_level -= 1
                if highest_level == 1:
                    rem_list.insert(0, i)

    # removes members without any songs left
    for i in rem_list:
        members.pop(i)

def make_squad_playlist(playlists):
    final_playlist = []
    squad_size = len(playlists)
    playlist_sizes = [len(playlist.tracks) for playlist in playlists]
    target_playlist_size = sum(playlist_sizes) / squad_size

    # convert playlists array to members 2d array
    members = playlists_to_members(playlists)
    
    # pops unnecessary rows from song lists
    rem_list = []
    for i, member in enumerate(members, start=0):
        level = squad_size
        while len(member.songs[level]) == 0 and level >= 2:
            member.songs.pop()
            level -= 1
        if level == 1:
            rem_list.insert(0, i)

    # removes members without any songs left
    for i in rem_list:
        members.pop(i)

    # step1: adds songs till each member meets the threshold
    thresh = target_playlist_size / (2 * squad_size)
    while not thresh_met(members, thresh):
        member = smallest_count(members)
        remove(member.songs[-1][0], len(member.songs) - 1, members, final_playlist)

    # step2: add most popular songs until reachest smalles level of songs which will be added
    step2 = True
    curr_level = squad_size
    while step2:
        songs_at_level = 0
        for member in members:
            if len(member.songs) - 1 == curr_level:
                songs_at_level += len(member.songs[curr_level])
        songs_at_level /= curr_level
        if songs_at_level <= target_playlist_size - len(final_playlist):
            for member in members:
                while len(member.songs) - 1 == curr_level:
                    remove(member.songs[curr_level][0], curr_level, members, final_playlist)
            curr_level -= 1
        else:
            step2 = False
        if curr_level < 2:
            step2 = False

    # step3: balances lowest level of songs added
    if len(members) > 0:
        while target_playlist_size - len(final_playlist) > 0:
            member = smallest_count(members)
            remove(member.songs[-1][0], curr_level, members, final_playlist)

    return final_playlist