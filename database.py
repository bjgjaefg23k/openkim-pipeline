""" 
Set of methods for querying the database in one form or the other

"""
from config import *
logger = logger.getChild("database")
import re, os, glob, operator

#-------------------------------------------------
# Helper routines (probably move)
#-------------------------------------------------

#KIMID matcher  ( optional name             __) (prefix  ) ( number  )( opt version )
RE_KIMID    = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{10,12})(?:_([0-9]{3}))?"
#FIXME : right now I let the numbers be between 10 and 12 because we have some that are screwed up


def new_test_result_id(number=None):
    """ Generate or get a new test result id, currently make them up, eventually request them from the website """
    if number:
        version = get_new_version(None,"TR",number)
        return format_kim_code(None,"TR",number,version)
    else:
        return kimid.new_kimid("TR")


def parse_kim_code(kim_code):
    """ Parse a kim code into it's pieces,
        returns a tuple (name,leader,num,version) """
    try:
        logger.debug("attempting to parse %r",kim_code)
        return re.match(RE_KIMID,kim_code).groups()
    except AttributeError:
        logger.error("Invalid KIMID on %r", kim_code)
        raise InvalidKIMID, "{}: is not a valid KIMID".format(kim_code)

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
    """ Get the new version code for the information given """
    version_int = int(get_latest_version(name,leader,num)) + 1
    return "{:03d}".format(version_int)

def format_kim_code(name,leader,num,version):
    """ Format a kim code into its proper form """
    assert leader, "we need a leader"
    assert num, "we need a number"
    assert version, "we need a version"
    if name:
        return "{}__{}_{}_{}".format(name,leader,num,version)
    else:
        return "{}_{}_{}".format(leader,num,version)


#--------------------------------
# some list generators 
#--------------------------------

