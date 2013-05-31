""" 
Set of methods for querying the database in one form or the other

As well as parsing and handling kim_codes

Currently these calls mostly glob on the database, could be replaced by something more elegant later

"""
from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("database")
import re, os, glob, operator
import kimobjects
import random
import kimservice
#-------------------------------------------------
# Helper routines (probably move)
#-------------------------------------------------

#KIMID matcher  ( optional name             __) (prefix  ) ( number  )( opt version )
RE_KIMID    = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?"

def new_test_result_id(number=None):
    """ Generate or get a new test result id, currently make them up, eventually request them from the website """
    if number:
        version = get_new_version(None,"TR",number)
        return format_kim_code(None,"TR",number,version)
    else:
        kim_code =  new_tr_kimid()
        logger.info("Generated new TR kim_code: %r", kim_code)
        return kim_code

def new_verification_result_id(number=None):
    """ Generate or get a new verification result id, currently make them up, eventually request them from the website """
    if number:
        version = get_new_version(None,"VR",number)
        return format_kim_code(None,"VR",number,version)
    else:
        kim_code =  new_vr_kimid()
        logger.info("Generated new VR kim_code: %r", kim_code)
        return kim_code

def randint():
    """ Return a random kim integer """
    return random.randint(0,1e12)

def new_tr_kimid():
    """ Generate a new Test Result kimid """
    existing = set( result.kim_code for result in kimobjects.TestResult.all() )
    kim_code = format_kim_code(None,"TR","{:012d}".format(randint()),"000")
    while kim_code in existing:
        kim_code = format_kim_code(None,"TR","{:012d}".format(randint()),"000")
    return kim_code

def new_vr_kimid():
    """ Generate a new Test Result kimid """
    existing = set( result.kim_code for result in kimobjects.VerificationResult.all() )
    kim_code = format_kim_code(None,"VR","{:012d}".format(randint()),"000")
    while kim_code in existing:
        kim_code = format_kim_code(None,"VR","{:012d}".format(randint()),"000")
    return kim_code

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
    """ Get the new version code for the information given, i.e. increments the
    largest version number found by 1 """
    version_int = int(get_latest_version(name,leader,num)) + 1
    return "{:03d}".format(version_int)

def format_kim_code(name,leader,num,version):
    """ Format a kim code into its proper form, assuming the form
        
        {name}__{leader}_{number}_{version}
    """
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

def test_model_to_priority(test,model):
    """ method to assign priorities to test model pairs, currently empty 

    .. todo::
        
        implements priorities
    """
    return 1


#======================================
# Some kim api wrapped things
#======================================

def valid_match(test,model):
    """ Test to see if a test and model match using the kim API, returns bool

        Tests through ``kimservice.KIM_API_init``, running in its own forked process
    """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    logger.debug("invoking KIMAPI for (%r,%r)",test,model)
    pid = os.fork()
    if (pid==0):
        logger.debug("in fork")
        match, pkim = kimservice.KIM_API_init(test.kim_code,model.kim_code)
        if match:
            kimservice.KIM_API_free(pkim)
            os._exit(0)
        os._exit(1)

    # try to get the exit code from the kim api process
    exitcode = os.waitpid(pid,0)[1]/256
    logger.debug("got exitcode: %r" , exitcode )
    if exitcode == 0:
        match = True
    elif exitcode == 1:
        match = False
    else:
        logger.error("We seem to have a Kim init error on (%r,%r)", test, model)
        raise KIMRuntimeError
        match = False

    if match:
        return True
    else:
        return False

