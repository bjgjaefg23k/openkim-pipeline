""" A pure python object wrapper for the pipeline stuff

What we would like is a nice way to create an manipulate the items in the database

Things we need to be able to do:
    * create test results
    * look up test results for test model pairs
    * look up current versions of kim objects

"""

from config import *
logger = logger.getChild("models")

from persistentdict import PersistentDict
import re, os, glob, operator
from contextlib import contextmanager
import kimid
import template

#-------------------------------------------------
# Helper routines (probably move)
#-------------------------------------------------

#KIMID matcher  ( optional name             __) (prefix  ) ( number  )( opt version )
RE_KIMID    = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{12})(?:_([0-9]{3}))?"


def parse_kim_code(kim_code):
    """ Parse a kim code into it's pieces,
        returns a tuple (name,leader,num,version) """
    try:
        return re.match(RE_KIMID,kim_code).groups()
    except AttributeError:
        logger.error("Invalid KIMID on %r", kim_code)
        raise InvalidKIMID, "{}: is not a valid KIMID".format(kim_code)

def kim_code_finder(name,leader,num,version):
    """ Do a glob to look for possible matches
        returns a list of possible matches, where the matches are kim_codes """
    start_path = os.path.join(KIM_REPOSITORY_DIR,leader.lower())
    name = name or '*'
    version = version or '*'
    kim_code = format_kim_code(name,leader,num,version)
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
    version = None
    possibilities = kim_code_finder(name,leader,num,version)
    parsed_possibilities = [ parse_kim_code(code) for code in possibilities ]
    #sort the list on its version number
    newest = sorted(parsed_possibilities,key=operator.itemgetter(-1)).pop()
    return newest

def format_kim_code(name,leader,num,version):
    """ Format a kim code into its proper form """
    if name:
        return "{}__{}_{}_{}".format(name,leader,num,version)
    else:
        return "{}_{}_{}".format(leader,num,version)

#------------------------------------------------
# Base KIMObject 
#------------------------------------------------

class KIMObject(object):
    """ The base KIMObject that all things inherit from
    
    KIMObjects live in memory, and have the following things:
        * path - directory they are stored
        * kim_code - their kim code
        * kim_code_leader - two letter prefix
        * kim_code_number - their id number (12 digits)
        * kim_code_version - 3 digit version number
        * info - some metadata stored in a json file
    """
    required_leader = None
    def __init__(self,kim_code):
        """ Initialize a KIMObject given the kim_code, where partial kim codes are promoted if possible """
        logger.debug("Initializing a new KIMObject: %r", kim_code)
        name, leader, num, version = parse_kim_code(kim_code)
       
        # test to see if we have the right leader
        if self.required_leader:
            assert leader==self.required_leader,"{} not a valid KIM code for {}".format(kim_code, self.__class__.__name__)
        
        #grab the attributes
        self.kim_code_name = name
        self.kim_code_leader = leader
        self.kim_code_number = num
        self.kim_code_version = version
        
        #if we were given everything, we are good to go
        if name and leader and num and version:
            self.kim_code = format_kim_code(name,leader,num,version)
        
        #if we weren't given a name, see if one exists
        elif name is None and leader and num and version:
            name = look_for_name(leader,num,version)
            self.kim_code_name = name
            self.kim_code = format_kim_code(name,leader,num,version)
        
        #if we weren't given a version
        elif name and leader and num and version is None:
            name,leader,num,version = get_latest_version(name,leader,num)
            self.kim_code_version = version
            self.kim_code = format_kim_code(name,leader,num,version)

        #if we weren't given a name or version
        elif name is None and leader and num and version is None:
            name,leader,num,version = get_latest_version(name,leader,num)
            self.kim_code_name = name
            self.kim_code_version = version
            self.kim_code = format_kim_code(name,leader,num,version)

        self.path = os.path.join(KIM_REPOSITORY_DIR,leader.lower(),self.kim_code)
        self.info = PersistentDict(os.path.join(self.path,METADATA_INFO_FILE))

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.kim_code)

    @property
    def exists(self):
        """ Tells you whether the path exists or not """
        return os.path.exists(self.path)

    def get_latest_version_number(self):
        """ Figure out the latest version number """
        name,leader,num,version = get_latest_version(self.kim_code_name,
                self.kim_code_leader,self.kim_code_number)
        return version
    
    @property
    def is_latest_version(self):
        """ Tells whether this is the latest version in the database """
        myversion = self.kim_code_version
        newestversion = self.get_latest_version_number()
        return myversion == newestversion

    def sync(self):
        """ Sync the info file """
        self.info.sync()

    @contextmanager
    def in_dir(self):
        """ a context manager to do things inside this objects path """
        cwd = os.getcwd()
        os.chdir(self.path)
        logger.debug("moved to dir: {}".format(self.path))
        yield
        os.chdir(cwd)




#---------------------------------------------
# Actual KIM Models
#---------------------------------------------

class Test(KIMObject):
    """ A kim test, it is a KIMObject, plus
    
        * executable - a path to its executable
        * in_file - it's infile
        * out_file - out_file dictionary
        * test_driver - which test driver it relies on
    """
    required_leader = "TE"
    def __init__(self,kim_code):
        """ Initialize the Test, with a kim_code """
        super(Test,self).__init__(kim_code)
        self.executable = os.path.join(self.path,self.kim_code)
        self.outfile_path = os.path.join(self.path,OUTPUT_FILE)
        self.infile_path = os.path.join(self.path,INPUT_FILE)
        self.out_dict = self._outfile_to_dict()

    @property
    def infile(self):
        """ return a file object for the in file """
        return open(self.infile_path)
    @property
    def outfile(self):
        """ return a file object for the out file """
        return open(self.outfile_path)

    def dependency_check(self):
        """ Ask template.py to do a dependency check
            returns a 3 tuple
                ready - bool of whether good to go or not
                dependencies_good_to_go - kids for ready dependencies
                dependencies_not_ready - tuples of test/model pairs to run """
        return template.dependency_check(self.infile)

    def _outfile_to_dict(self):
        """ Convert the output file to a dict """
        outdata = open(self.outfile_path).read()
        lines = outdata.splitlines()
        data = {}
        for line in lines:
            front,back = line.split(":")
            data.update({ front.strip() : back.strip() })
        return data



class Model(KIMObject):
    """ A KIM Model """
    required_leader = "MO"
    def __init__(self,kim_code):
        """ Initialize the Model, with a kim_code """
        super(Model,self).__init__(kim_code)

class TestResult(KIMObject):
    """ A test result """
    required_leader = "TR"
    def __init__(self,kim_code):
        """ Initialize the TestResult, with a kim_code """
        super(TestResult,self).__init__(kim_code)

class TestDriver(KIMObject):
    """ A test driver """
    required_leader = "TD"
    def __init__(self,kim_code):
        """ Initialize the TestDriver, with a kim_code """
        super(TestDriver,self).__init__(kim_code)

class ModelDriver(KIMObject):
    """ A model driver """
    required_leader = "MD"
    def __init__(self,kim_code):
        """ Initialize the ModelDriver, with a kim_code """
        super(ModelDriver,self).__init__(kim_code)

class Property(KIMObject):
    """ A kim property """
    required_leader = "PR"
    def __init__(self,kim_code):
        """ Initialize the Property, with a kim_code """
        super(Property,self).__init__(kim_code)

class VerificationCheck(KIMObject):
    """ A verification check """
    required_leader = "VC"
    def __init__(self,kim_code):
        """ Initialize the VerificationCheck, with a kim_code """
        super(VerificationCheck,self).__init__(kim_code)

class VerificationResult(KIMObject):
    """ A verification result """
    required_leader = "VR"
    def __init__(self,kim_code):
        """Initialize the VerificationResult, with a kim_code """
        super(VerificationResult,self).__init__(kim_code)


class ReferenceDatum(KIMObject):
    """ a piece of reference data """
    required_leader = "RD"
    def __init__(self,kim_code):
        """ Initialize the ReferenceDatum, with a kim_code """
        super(ReferenceDatum,self).__init__(kim_code)

class VirtualMachine(KIMObject):
    """ for a virtual machine """
    required_leader = "VM"
    def __init__(self,kim_code):
        """ Initialize a VirtualMachine with a kim_code """
        super(VirtualMachine,self).__init__(kim_code)
