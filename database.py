""" 
Set of methods for querying the database in one form or the other

As well as parsing and handling kim_codes

Currently these calls mostly glob on the database, could be replaced by something more elegant later

"""
from config import *
import re, os, glob, operator

from logger import logging
logger = logging.getLogger("pipeline").getChild("database")

#-------------------------------------------------
# Helper routines (probably move)
#-------------------------------------------------
#KIMID matcher  ( optional name             __) (prefix  ) ( number  )( opt version )
RE_KIMID    = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?"
RE_UUID     = r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})"

def parse_kim_code(kim_code):
    """ Parse a kim code into it's pieces,
        returns a tuple (name,leader,num,version) """
    try:
        logger.debug("attempting to parse %r",kim_code)
        return re.match(RE_KIMID,kim_code).groups()
    except AttributeError:
        try:
            logger.debug("attempting to parse uuid %r", kim_code)
            return re.match(RE_UUID, kim_code).groups()
        except AttributeError:
            logger.error("Invalid KIMID on %r", kim_code)
            raise InvalidKIMID, "{}: is not a valid KIMID".format(kim_code)

def isuuid(kimcode):
    return len(parse_kim_code(kimcode)) == 1

def kim_code_finder(name,leader,num,version):
    """ Do a glob to look for possible matches
        returns a list of possible matches, where the matches are kim_codes """
    logger.debug("looking up kim_code for (%r,%r,%r,%r)", name,leader,num,version)
    start_path = os.path.join(KIM_REPOSITORY_DIR,leader.lower())
    name = name
    version = version or '*'
    kim_code = format_kim_code(name,leader,num,version)
    if not name:
        kim_code = "*"+kim_code

    full_possibilities = glob.glob(os.path.join(start_path,kim_code))
    short_possibilities = [ os.path.basename(x) for x in full_possibilities ]

    if len(short_possibilities) == 0:
        #none found
        logger.error("Failed to find any matches for %r", kim_code)
        raise PipelineSearchError, "Failed to find any matches for {}".format(kim_code)
    return short_possibilities


def look_for_name(leader,num,version):
    """ Look for a name given the other pieces of a kim code,
        returns just the name if it exists or throws and error"""
    partial = format_kim_code(None,leader,num,version) 
    logger.debug("looking up names for %r", partial)
    possibilities = kim_code_finder(None,leader,num,version)
    if len(possibilities) == 1:
        fullname = possibilities[0]
        name, leader, num, version = parse_kim_code(fullname)
        return name
    #must be multiple possibilities
    logger.error("Found multiple names for %r", partial)
    raise PipelineTemplateError, "Found multiple matches for {}".format(partial)

def get_latest_version(name,leader,num):
    """ Get the latest version of the kim code in the database,
    return the full kim_code for the newest version in the database"""
    logger.debug("Looking for the newest verison of (%r,%r,%r)",name,leader,num)
    version = None
    possibilities = kim_code_finder(name,leader,num,version)
    parsed_possibilities = [ parse_kim_code(code) for code in possibilities ]
    #sort the list on its version number
    newest = sorted(parsed_possibilities,key=operator.itemgetter(-1)).pop()
    return newest

def get_new_version(name,leader,num):
    """ Get the new version code for the information given, i.e. increments the
    largest version number found by 1 """
    version_int = int(get_latest_version(name,leader,num)) + 1
    return "{:03d}".format(version_int)

def get_leader(kimcode):
    if uuid_type(kimcode):
        return uuid_type(kimcode)
    try:
        name,leader,num,ver = parse_kim_code(kimcode)
        return leader
    except:
        return None

def format_kim_code(name,leader,num,version):
    """ Format a kim code into its proper form, assuming the form
        
        {name}__{leader}_{number}_{version}
    """
    assert leader, "we need a leader"
    assert num, "we need a number"
    assert version, "we need a version"
    if name:
        if version:
            return "{}__{}_{}_{}".format(name,leader,num,version)
        else:
            return "{}__{}_{}".format(name,leader,num)
    else:
        return "{}_{}_{}".format(leader,num,version)

def uuid_type(uuid):
    tries = ['tr', 'vr', 'er']
    for leader in tries:
        if os.path.exists(os.path.join(RSYNC_LOCAL_ROOT, leader, uuid)):
            return leader
    return None

def strip_version(kimcode):
    name, leader, num, version = parse_kim_code(kimcode)
    return "{}__{}_{}".format(name, leader, num)

#--------------------------------
# some list generators 
#--------------------------------
def test_model_to_priority(test,model):
    """ method to assign priorities to test model pairs, currently empty 

    .. todo::
        
        implements priorities
    """
    return 1

