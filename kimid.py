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

from persistentdict import PersistentDict, PersistentDefaultDict
import random, sys
from config import *
import repository
from contextlib import nested
import re
from template import RE_KIMID

logger = logger.getChild("kimid")
""" 
The dictionary of ids is a layered dictionary, or leader, then id then version
"""


NUM_DIGITS = 12
VERSION_DIGITS = 3
KIM_NAME_FORMAT = "{}__{}"
KIM_ID_FORMAT = "{}_{}_{:03d}"
STORE_FILENAME = KIMID_STORE
ALLOWED_LEADERS = ["MO","MD","ME","TE","TD","PR","TR","RD","VC","VR"]
FORMAT = "json"

def randints():
    while True:
        yield random.randint(0,10**NUM_DIGITS-1)

randints_gen = randints()

def next_int(collection):
    return next( "{:012d}".format(x) for x in randints_gen if x not in collection )


def get_new_id(leader):
    """ Generate a new KIM ID """
    with PersistentDefaultDict(STORE_FILENAME, format=FORMAT) as store:
        pk = next_int(store[leader])
        version = 0
        store[leader][pk] = version
    newkimid = KIM_ID_FORMAT.format(leader,pk,version)
    logger.info("Generated new KIMID: {}".format(newkimid))
    return newkimid

def get_new_version(leader,pk):
    """ Get the next version number """
    pk = str(pk)
    with PersistentDefaultDict(STORE_FILENAME, format=FORMAT) as store:
        version = store[leader][pk]
        version += 1
        store[leader][pk] = version
    newkimid = KIM_ID_FORMAT.format(leader,pk,version)
    logger.info("Requested new version KIMID: {}".format(newkimid))
    return newkimid


def get_current_version(leader,pk):
    """ Get the current version number """
    pk = str(pk)
    with PersistentDefaultDict(STORE_FILENAME, format=FORMAT, flag='r') as store:
        version = store[leader][pk]
    return version

def promote_kimid(kid):
    """ Given a kimid {kid}, with or without the version number,
        with or without the prepended name, ensure that the most complete kimid comes out
    """
    if not re.match(RE_KIMID,kid):
        raise PipelineTemplateError, "what I got {} is not a valid kimid"
    try:
        name,kid = kid.split("__")
    except ValueError:
        #we don't seem to have a name
        #get the name from the store
        with PersistentDefaultDict(NAME_STORE) as store:
            name = store[kid]
    else:
        # we must have split successfully to be here
        #we have at least a name
        pass
    finally:
        #check to see if we are short
        if len(kid) == 2 + 1 + NUM_DIGITS: # (TE) + (_) + (0123456789012)
            # we have a short id
            leader, pk = kid.split("_")
            version = get_current_version(leader,pk)
        else:
            _,leader,pk,version = parse_kimid(kid)

        fullkid = format_kimid(leader,pk,version,name)
        return fullkid

def format_kimid(leader,pk,version,front=None):
    if isinstance(pk,int):
        pk = "{:012d}".format(pk)

    kid = KIM_ID_FORMAT.format(leader,pk,version)
    if front:
        return KIM_NAME_FORMAT.format(front,kid)
    return kid

def parse_kimid(kim_name):
    """given an id return a tuple of its parts"""
    try:
        #see if we have a front
        front, back = kim_name.split("__")
    except ValueError:
        #looks like we don't have a front 
        front = None
        back = kim_name
    parts = back.split("_")
    leader, pk, version = parts
    version = int(version)
    return (front,leader,pk,version)

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
            with PersistentDefaultDict(STORE_FILENAME, format=FORMAT) as store:
                for leader in ALLOWED_LEADERS:
                    store[leader] = {}


