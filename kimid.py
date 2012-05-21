"""
Handles handing out KIM IDs

which is of the form
    CC_DDDDDDDD_VVV
    where CC is:
        MO - Model
        MD - Model Driver
        ME - Model Ensemble
        TE - Test
        TD - Test Driver
        PR - Property
        RD - Reference data
        *PD - Prediction

"""

from persistentdict import PersistentDict
import random, sys

""" 
The dictionary of ids is a layered dictionary, or leader, then id then version
"""


NUM_DIGITS = 8
KIM_ID_FORMAT = "{}_{}_{:03d}"
STORE_FILENAME = "kimidstore.json"
ALLOWED_LEADERS = ["MO","MD","ME","TE","TD","PR","RD","PD"]
FORMAT = "json"

def randints():
    while True:
        yield random.randint(0,10**NUM_DIGITS-1)

def next_int(collection):
    return next( "{:08d}".format(x) for x in randints() if x not in collection )


def get_new_id(leader):
    """ Generate a new KIM ID """
    with PersistentDict(STORE_FILENAME, format=FORMAT) as store:
        pk = next_int(store[leader])
        version = 0
        store[leader][pk] = version
    return KIM_ID_FORMAT.format(leader,pk,version)

def get_new_version(leader,pk):
    """ Get the next version number """
    pk = str(pk)
    with PersistentDict(STORE_FILENAME, format=FORMAT) as store:
        version = store[leader][pk]
        version += 1
        store[leader][pk] = version
    return KIM_ID_FORMAT.format(leader,pk,version)


def get_current_version(leader,pk):
    """ Get the current version number """
    pk = str(pk)
    with PersistentDict(STORE_FILENAME, format=FORMAT, flag='r') as store:
        version = store[leader][pk]
    return version

def format_kimid(leader,pk,version):
    if isinstance(pk,int):
        pk = "{:08d}".format(pk)
    return KIM_ID_FORMAT.format(leader,pk,version)


def new_kimid(leader,pk=None):
    """ Generate a new kim id, if only the leader is given generate a new id number,
    if the id number is given, increment the version number """
    if pk is None:
        return get_new_id(leader)
    else:
        return get_new_version(leader,pk)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            print "Generating empty store in {}".format(STORE_FILENAME)
            with PersistentDict(STORE_FILENAME, format=FORMAT) as store:
                for leader in ALLOWED_LEADERS:
                    store[leader] = {}

