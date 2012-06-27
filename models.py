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
from contextlib import contextmanager
import template
import database
import shutil
import subprocess
import re
import dircache


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
    makeable = False

    def __init__(self,kim_code):
        """ Initialize a KIMObject given the kim_code, where partial kim codes are promoted if possible """
        logger.debug("Initializing a new KIMObject: %r", kim_code)
        name, leader, num, version = database.parse_kim_code(kim_code)
       
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
            self.kim_code = database.format_kim_code(name,leader,num,version)
        
        #if we weren't given a name, see if one exists
        elif name is None and leader and num and version:
            name = database.look_for_name(leader,num,version)
            self.kim_code_name = name
            self.kim_code = database.format_kim_code(name,leader,num,version)
        
        #if we weren't given a version
        elif name and leader and num and version is None:
            name,leader,num,version = database.get_latest_version(name,leader,num)
            self.kim_code_version = version
            self.kim_code = database.format_kim_code(name,leader,num,version)

        #if we weren't given a name or version
        elif name is None and leader and num and version is None:
            name,leader,num,version = database.get_latest_version(name,leader,num)
            self.kim_code_name = name
            self.kim_code_version = version
            self.kim_code = database.format_kim_code(name,leader,num,version)

        self.parent_dir = os.path.join(KIM_REPOSITORY_DIR, self.kim_code_leader.lower())
        self.path = os.path.join( self.parent_dir ,self.kim_code)
        self.info = PersistentDict(os.path.join(self.path,METADATA_INFO_FILE))

    def __str__(self):
        return self.kim_code

    def __repr__(self):
        return "<{}({})>".format(self.__class__.__name__, self.kim_code)

    def __hash__(self):
        return hash(self.kim_code)

    def __eq__(self,other):
        if other:
            return  str(self) == str(other)
        return False

    def __nonzero__(self):
        """ Object is true if it exists """
        return self.exists

    @property
    def exists(self):
        """ Tells you whether the path exists or not """
        return os.path.exists(self.path)

    def get_latest_version_number(self):
        """ Figure out the latest version number """
        name,leader,num,version = database.get_latest_version(self.kim_code_name,
                self.kim_code_leader,self.kim_code_number)
        return version

    @property
    def latest_version(self):
        """ Return the latest version object of this thing """
        name,leader,num,version = database.get_latest_version(self.kim_code_name, self.kim_code_leader, self.kim_code_number)
        return self.__class__(database.format_kim_code(name,leader,num,version))
    
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
    
    def make(self):
        """ Try to build the thing """
        if self.makeable:
            with self.in_dir():
                logger.debug("Attempting to make %r: %r", self.__class__.__name__, self.kim_code)
                subprocess.check_call('make')
        else:
            logger.warning("%r:%r is not makeable", self.__class__.__name__, self.kim_code)

    @property
    def makefile(self):
        """ A file object for the make file """
        if self.makeable:
            return open(os.path.join(self.path, "Makefile"))
        else:
            logger.warning("%r:%r is not makeable", self.__class__.__name__, self.kim_code)

    @classmethod
    def all(cls):
        """ Return a generator of all of this type """
        logger.debug("Attempting to find all %r...", cls.__name__)
        type_dir = os.path.join(KIM_REPOSITORY_DIR, cls.required_leader.lower() ) 
        kim_codes =  ( subpath for subpath in dircache.listdir(type_dir) if os.path.isdir( os.path.join( type_dir, subpath) ) )
        return ( cls(x) for x in kim_codes )

#---------------------------------------------
# Actual KIM Models
#---------------------------------------------


#---------------------------------------------
# Test
#---------------------------------------------

class Test(KIMObject):
    """ A kim test, it is a KIMObject, plus
    
        * executable - a path to its executable
        * in_file - it's infile
        * out_file - out_file dictionary
        * test_driver - which test driver it relies on
    """
    required_leader = "TE"
    makeable = True

    def __init__(self,kim_code):
        """ Initialize the Test, with a kim_code """
        super(Test,self).__init__(kim_code)
        self.executable = os.path.join(self.path,self.kim_code)
        self.outfile_path = os.path.join(self.path,OUTPUT_FILE)
        self.infile_path = os.path.join(self.path,INPUT_FILE)
        self.out_dict = self._outfile_to_dict()

    def __call__(self,*args,**kwargs):
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)

    @property
    def _reversed_out_dict(self):
        """ Reverses the out_dict """
        return { value:key for key,value in self.out_dict.iteritems() }

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

    @property
    def dependencies(self):
        """ Return a list of kim objects that are its dependencies """
        ready, goods, bads = self.dependency_check()
        if goods:
            for kim_code in goods:
                yield kim_obj(kim_code)
        if bads:
            for kim1, kim2 in bads:
                yield kim_obj(kim1)
                yield kim_obj(kim2)

    @property
    def test_drivers(self):
        """ Return a list of test drivers this guy relies on """
        return ( depend for depend in self.dependencies if depend.required_leader == "TD")

    @property
    def results(self):
        """ Give a list of all of the results of this test """
        return ( result for result in TestResult.all() if result.test == self )

    def result_with_model(self, model):
        """ Get the first result with the model: model, or None """
        try:
            return next( result for result in self.results if result.model == model )
        except StopIteration:
            raise PipelineDataMissing, "Could not find a TestResult for (%r, %r)".format(self,model)
    
    def _outfile_to_dict(self):
        """ Convert the output file to a dict """
        outdata = open(self.outfile_path).read()
        lines = outdata.splitlines()
        data = {}
        for line in lines:
            front,back = line.split(":")
            data.update({ front.strip() : back.strip() })
        return data

    def processed_infile(self,model):
        """ Process the input file, with template, and return a file object to the result """
        template.process(self.infile,self.kim_code,model.kim_code)
        return open(os.path.join(self.path,TEMP_INPUT_FILE))


#--------------------------------------
# Model
#-------------------------------------

class Model(KIMObject):
    """ A KIM Model """
    required_leader = "MO"
    makeable = True

    def __init__(self,kim_code):
        """ Initialize the Model, with a kim_code """
        super(Model,self).__init__(kim_code)

    @property
    def model_driver(self):
        """ Return the model driver if there is one, otherwise None """
        try:
            return ModelDriver(next( line.split(":=")[1].strip() for line in self.makefile if line.startswith("MODEL_DRIVER_NAME") ))
        except StopIteration:
            return None

    @property
    def results(self):
        """ Get all of the results """
        return ( result for result in TestResult.all() if result.model == self )


#-------------------------------------
# TestResult
#-------------------------------------

class TestResult(KIMObject):
    """ A test result """
    required_leader = "TR"
    makeable = False

    def __init__(self, kim_code = None, pair = None, results = None):
        """ Initialize the TestResult, with a kim_code,
                or a (test,model) pair,
                optionally, take a JSON string and store it """
        
        if pair and kim_code:
            raise SyntaxWarning, "TestResult should have a pair, or a kim_code or neither, not both"
        
        if pair:
            test, model = pair
            result = test.result_with_model(model)
            kim_code = result.kim_code
        
        else:
            kim_code = kim_code or database.new_test_result_id()
        
        super(TestResult,self).__init__(kim_code)

        self.results = PersistentDict(os.path.join(self.path,self.kim_code),format='json')
        #if we recieved a json string, write it out
        if results:
            logger.debug("Recieved results, writing out to %r", self.kim_code)
            incoming_results = simplejson.loads(results)
            
            #also move all of the files
            files = template.files_from_results(incoming_results)
            if files:
                logger.debug("found files to move")
                testdir = Test(testname).path
                for src in files:
                    logger.debug("copying %r over", src)
                    shutil.copy(os.path.join(testdir,src),self.path)

            self.results.update(incoming_results)
            self.results.sync()

        self.test = Test(self.results["_testname"])
        self.model = Model(self.results["_modelname"])

    def sync(self):
        """ sync not only the info file but also the results """
        self.info.sync()
        self.results.sync()

    @property
    def files(self):
        """ A list of all of the files in the test_result """
        return map(os.path.basename,template.files_from_results(self.results))
    
    @property
    def full_file_paths(self):
        """ Files with a full path """
        return ( os.path.join(self.path, filename) for filename in self.files )

    @property
    def file_handlers(self):
        """ return file handlers for all of the files """
        return ( open(filename) for filename in self.full_file_paths )

    def _is_property(self,key):
        """ Tells whether a key is a property or not """
        return bool(re.match(database.RE_KIMID, key))

    @property
    def property_codes(self):
        """ Return a list of all property codes computed in this test result """
        return ( x for x in filter(self._is_property, self.results.keys() ) )    

    @property
    def predictions(self):
        """ Return a dictionary with kim Property objects pointing to the results """
        return { Property(key): value for key,value in self.results.iteritems() if key in self.property_codes }

    @property
    def properties(self):
        """ Return a list of properties """
        return ( Property(x) for x in self.property_codes )

    def __getitem__(self,key):
        """ Make it so that results behave like their result dictionary for access """
        return self.results.__getitem__(key)

    def __getattr__(self,attr):
        """ if we didn't find the attr, look in self.results """
        return self.results.__getattribute__(attr)

    @classmethod
    def test_result_exists(cls,test,model):
        """ Check to see if the test result exists """
        try:
            cls(pair=(test,model))
        except PipelineDataMissing:
            return False
        return True






#------------------------------------------
# TestDriver
#------------------------------------------

class TestDriver(KIMObject):
    """ A test driver """
    required_leader = "TD"
    makeable = True

    def __init__(self,kim_code):
        """ Initialize the TestDriver, with a kim_code """
        super(TestDriver,self).__init__(kim_code)
        self.executable = os.path.join(self.path, self.kim_code)

    def __call__(self,*args,**kwargs):
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)

    @property
    def tests(self):
        """ Return a list of tests """
        return ( test for test in Test.all() if self in test.dependencies )


#------------------------------------------
# ModelDriver
#------------------------------------------

class ModelDriver(KIMObject):
    """ A model driver """
    required_leader = "MD"
    makeable = True

    def __init__(self,kim_code):
        """ Initialize the ModelDriver, with a kim_code """
        super(ModelDriver,self).__init__(kim_code)

    @property
    def models(self):
        """ Return all of the models using this model driver """
        return ( model for model in Model.all() if self==model.model_driver )


#------------------------------------------
# Property
#------------------------------------------

class Property(KIMObject):
    """ A kim property """
    required_leader = "PR"
    makeable = False

    def __init__(self,kim_code):
        """ Initialize the Property, with a kim_code """
        super(Property,self).__init__(kim_code)

    @property
    def results(self):
        """ Return a list of results that compute this property """
        return ( tr for tr in TestResult.all() if self in tr.properties )

    @property
    def data(self):
        """ Return the data in this thing """
        return None

    @property
    def references(self):
        """ Return a generator of references that reference this property """
        return ( rd for rd in ReferenceDatum.all() if self == rd.property )

    @property
    def tags(self):
        """ Return a generator of all the tags used by the test writers to refer to this property """ 
        return set( value for key,value in result.test._reversed_out_dict.iteritems() if Property(key)==self for result in self.results )

    

#------------------------------------------
# VerificationCheck
#------------------------------------------

class VerificationCheck(KIMObject):
    """ A verification check """
    required_leader = "VC"
    makeable = True

    def __init__(self,kim_code):
        """ Initialize the VerificationCheck, with a kim_code """
        super(VerificationCheck,self).__init__(kim_code)
        self.executable = os.path.join(self.path,self.kim_code)

    def __call__(self,*args,**kwargs):
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)

#------------------------------------------
# VerificationResult
#------------------------------------------

class VerificationResult(KIMObject):
    """ A verification result """
    required_leader = "VR"
    makeable = False

    def __init__(self,kim_code):
        """Initialize the VerificationResult, with a kim_code """
        super(VerificationResult,self).__init__(kim_code)


#------------------------------------------
# ReferenceDatum
#------------------------------------------

class ReferenceDatum(KIMObject):
    """ a piece of reference data """
    required_leader = "RD"
    makeable = False

    def __init__(self,kim_code):
        """ Initialize the ReferenceDatum, with a kim_code """
        super(ReferenceDatum,self).__init__(kim_code)

#------------------------------------------
# VirtualMachine
#------------------------------------------

class VirtualMachine(KIMObject):
    """ for a virtual machine """
    required_leader = "VM"
    makeable = False

    def __init__(self,kim_code):
        """ Initialize a VirtualMachine with a kim_code """
        super(VirtualMachine,self).__init__(kim_code)


# two letter codes to the associated class
code_to_model = {"TE": Test, "MO": Model, "TD": TestDriver, "TR": TestResult , "VC": VerificationCheck, "VR": VerificationResult, "RD": ReferenceDatum, "PR": Property , "VM": VirtualMachine, "MD": ModelDriver }

def kim_obj(kim_code):
    """ Just given a kim_code try to make the right object """
    name,leader,num,version = database.parse_kim_code(kim_code)
    cls = code_to_model.get(leader, KIMObject)
    return cls(kim_code)



if __name__ == "__main__":
    result = TestResult("TR_127663948908_000")
