# placehold vars
member_num = 4 # number of squad members
target_len = 30 # can make a fn reletive to member_num
thresh = 3 #target_len/(2*member_num) # threshold size for each person
playlist = [] # final playlist
members = []

class Member:
    def __init__(self, name, member_num):
        self.name = name
        self.count = 0
        self.songs = [member_num + 1][0]

Nick = Member("Nick", member_num)
Thomas = Member("Thomas", member_num)
Hershal = Member("Hershal", member_num)
Justin = Member("Justin", member_num)
Nick.songs = [[], [], ["Kickstarts"], ["Fever Dream"], ["Kids"]]
Thomas.songs = [[], [], ["Kickstarts"], ["Fever Dream", "Dear Maria"], ["Kids"]]
Hershal.songs = [[], [], ["High Hopes"], ["Fever Dream", "Dear Maria"], ["Kids"]]
Justin.songs = [[], [], ["High Hopes"], ["Dear Maria"], ["Kids"]]
members = [Nick, Thomas, Justin, Hershal]

# checks if threshold is met for all members
def thresh_met():
    ret = True
    for member in members:
        if member.count < thresh:
            ret = False
    return ret 

# returns the member with smallest count
def smallest_count():
    smallest_member = members[0]
    smallest_count = members[0].count
    for member in members:
        if member.count < smallest_count:
            smallest_member = member
            smallest_count = member.count
    return smallest_member 

# removes a song from all members, increments count
def remove(song, level):
    rem_list = []
    playlist.append(song)
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


# also! edge case if all songs are gone, just stops code...
#probably dont need to code anything since and for each member loops will just do nothing

# main

# pops unnecessary rows from song lists
rem_list = []
for member in members:
    level = member_num
    while len(member.songs[level]) == 0 and level >= 2:
        member.songs.pop()
        level -= 1
    if level == 1:
        rem_list.insert(0, level)
    
# removes members without any songs left
for i in rem_list:
    members.pop(i)

# adds songs till each member meets the threshold
while not thresh_met():
    member = smallest_count()
    remove(member.songs[-1][0], len(member.songs) - 1)

print(playlist)