import shortuuid

def create_election_code():

    election_code = shortuuid.ShortUUID().random(length= 8)

    return election_code