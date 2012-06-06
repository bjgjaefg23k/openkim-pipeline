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
        PR - Prediction
        PO - Property
        RD - Reference data

"""

from persistentdict import PersistentDict
import random, sys
from config import *

logger = logger.getChild("kimid")
""" 
The dictionary of ids is a layered dictionary, or leader, then id then version
"""


NUM_DIGITS = 12
VERSION_DIGITS = 3
KIM_ID_FORMAT = "{}_{}_{:03d}"
STORE_FILENAME = KIMID_STORE
ALLOWED_LEADERS = ["MO","MD","ME","TE","TD","PR","PO","RD"]
FORMAT = "json"

def randints():
    while True:
        yield random.randint(0,10**NUM_DIGITS-1)

randints_gen = randints()

def next_int(collection):
    return next( "{:08d}".format(x) for x in randints_gen if x not in collection )


def get_new_id(leader):
    """ Generate a new KIM ID """
    with PersistentDict(STORE_FILENAME, format=FORMAT) as store:
        pk = next_int(store[leader])
        version = 0
        store[leader][pk] = version
    newkimid = KIM_ID_FORMAT.format(leader,pk,version)
    logger.info("Generated new KIMID: {}".format(newkimid))
    return newkimid

def get_new_version(leader,pk):
    """ Get the next version number """
    pk = str(pk)
    with PersistentDict(STORE_FILENAME, format=FORMAT) as store:
        version = store[leader][pk]
        version += 1
        store[leader][pk] = version
    newkimid = KIM_ID_FORMAT.format(leader,pk,version)
    logger.info("Requested new version KIMID: {}".format(newkimid))
    return newkimid


def get_current_version(leader,pk):
    """ Get the current version number """
    pk = str(pk)
    with PersistentDict(STORE_FILENAME, format=FORMAT, flag='r') as store:
        version = store[leader][pk]
    return version

def promote_kimid(kid):
    """ Given a kimid {kid}, with or without the version number,
        ensure it goes out with the version number """
    if len(kid) == 2+1+NUM_DIGITS:
        #we have a short id
        leader,pk = kid.split("_")
        version = get_current_version(leader,pk)
        return format_kimid(leader,pk,version)
    return kid


def format_kimid(leader,pk,version):
    if isinstance(pk,int):
        pk = "{:08d}".format(pk)
    return KIM_ID_FORMAT.format(leader,pk,version)

def parse_kimid(kimid):
    """given an id return a tuple of its parts"""
    parts = kimid.split("_")
    leader, pk, version = parts
    version = int(version)
    return (leader,pk,version)

def new_kimid(leader,pk=None):
    """ Generate a new kim id, if only the leader is given generate a new id number,
    if the id number is given, increment the version number
        
        meant to be the main method of this class 
    """
    logger.debug("inside new_kimid")
    if pk is None:
        return get_new_id(leader)
    else:
        return get_new_version(leader,pk)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "init":
            logger.info("Generating empty store in {}".format(STORE_FILENAME))
            with PersistentDict(STORE_FILENAME, format=FORMAT) as store:
                for leader in ALLOWED_LEADERS:
                    store[leader] = {}


