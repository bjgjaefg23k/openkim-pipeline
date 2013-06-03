"""
@@.. module:: models
    :synopsis: Holds the python object models for kim objects

.. moduleauthor:: Alex Alemi <alexalemi@gmail.com>

A pure python object wrapper for the pipeline stuff

Has a base ``KIMObject`` class and

 * Test
 * Model
 * TestResult
 * TestDriver
 * ModelDriver
 * Property
 * ReferenceDatum
 * VerificationCheck
 * VerificationResult
 * VirtualMachine

classes, all of which inherit from ``KIMObject`` and aim to know how to handle themselves.

"""

from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("kimobjects")

from persistent import PersistentDict
from contextlib import contextmanager
import template
import database
import kimapi
import shutil
import subprocess
import re
import dircache
import simplejson, yaml
from template import template_environment
import random

#------------------------------------------------
# Base KIMObject
#------------------------------------------------

class KIMObject(simplejson.JSONEncoder):
    """ The base KIMObject that all things inherit from

    Attributes:
        required_leader
            the required two letter leader for all kim codes, meant to be overridden
            by subclassers
        makeable
            marks the type of kimobject as makeable or not, to be overriden by subclassers
        path
            the full path to the directory associated with the kim object
        kim_code
            the full kim_code
        kim_code_name
            the name at the front of the kim_code or None
        kim_code_leader
            the two digit prefix
        kim_code_number
            the 12 digit number as string
        kim_code_version
            the version number as string
        parent_dir
            the parent directory of the object, i.e. the ``te`` directory for a test object

    """
    #the required leader to this classes kim_codes
    required_leader = None
    #whether or not objects of this type are makeable
    makeable = False

    def __init__(self,kim_code,search=True,subdir=None):
        """ Initialize a KIMObject given the kim_code, where partial kim codes are promoted if possible,
            if search is False, then don't look for existing ones

            Args:
                kim_code (str)
                    A full or partial kim_code, i.e. one like:
                     * "Full_Name_of_thing__TE_000000000000_000"
                     * "TE_000000000000_000"
                     * "TE_000000000000"
                     * "Full_Name_of_thing__TE_000000000000"
                search (bool)
                    Whether or not to search the directory structure for the fullest match,
                    false is useful when creating new KIMObjects to avoid hitting a PipelineSearchError
                dirpath (str)
                    In order to point to a directory that does not follow that pattern
                    /home/vagrant/openkim-repository/{mo,md,te...}/KIM_CODE/KIM_CODE
                    can provide the folder of
                    /home/vagrant/openkim-repository/{mo,md,te...}/SUBDIR/KIM_CODE
        """
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
        self.kim_code_id = leader+"_"+num+"_"+version

        if not search:
            self.kim_code = kim_code
        #if we were given everything, we are good to go
        elif name and leader and num and version:
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
        if subdir is not None:
            self.path = os.path.join(self.parent_dir, subdir)
        else:
            self.path = os.path.join(self.parent_dir, self.kim_code)

    def __str__(self):
        """ the string representation is the full kim_code """
        return self.kim_code

    def __repr__(self):
        """ The repr is of the form <KIMObject(kim_code)> """
        return "<{}({})>".format(self.__class__.__name__, self.kim_code)

    def __hash__(self):
        """ The hash is the full kim_code """
        return hash(self.kim_code)

    def __eq__(self,other):
        """ Two KIMObjects are equivalent if their full kim_code is equivalent """
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

    def create_dir(self):
        """ If this thing doesn't exist create it's directories """
        if not self.exists:
            os.makedirs(self.path)

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

    @contextmanager
    def in_dir(self):
        """ a context manager to do things inside this objects path
            Usage::

                foo = KIMObject(some_code)
                with foo.in_dir():
                    # < code block >

            before executing the code block, cd into the path of the kim object
            execute the code and then come back to the directory you were at
        """
        cwd = os.getcwd()
        os.chdir(self.path)
        logger.debug("moved to dir: {}".format(self.path))
        
        try:
            yield
        except Exception as e:
            raise e
        finally:
            os.chdir(cwd)

    def make(self):
        """ Try to build the thing, by executing ``make`` in its directory """
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

    def delete(self):
        """ Delete the folder for this object

            .. note::

                Not to be used lightly!
        """
        logger.warning("REMOVING the kim object %r", self)
        shutil.rmtree(self.path)

#=============================================
# Actual KIM Models
#=============================================

#--------------------------------------------
# Meta Guys
#--------------------------------------------

class Runner(KIMObject):
    """ A Runner, something that runs things
    either a test or a verification check of sorts """
    makeable = True
    def __init__(self,kim_code,*args,**kwargs):
        super(Runner,self).__init__(kim_code,*args,**kwargs)
        self.executable = os.path.join(self.path,self.kim_code)
        self.infile_path = os.path.join(self.path,INPUT_FILE)

    def __call__(self,*args,**kwargs):
        """ Calling a runner object executes its executable in
        its own direcotry.  args and kwaargs are passed to ``subprocess.check_call``. """
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)

    @property
    def _reversed_out_dict(self):
        """ Reverses the out_dict """
        return { value:key for key,value in self.out_dict.iteritems() }

    @property
    def infile(self):
        """ return a file object for the INPUT_FILE """
        return open(self.infile_path)

    def dependency_check(self, subject=None):
        """ Ask template.py to do a dependency check
            returns a 3 tuple
                ready - bool of whether good to go or not
                dependencies_good_to_go - kids for ready dependencies
                dependencies_not_ready - tuples of test/model pairs to run """
        if subject:
            return template.dependency_check(self.modelname_processed_infile(subject))
        return template.dependency_check(self.infile,model=False)

    @property
    def dependencies(self):
        """ Return a generator of kim objects that are its dependencies """
        ready, goods, bads = self.dependency_check()
        if goods:
            for guy in goods:
                yield guy
        if bads:
            for guy1, guy2 in bads:
                yield guy1
                yield guy2

    @property
    def results(self):
        """ Return a generator of all of the results of this test """
        return ( result for result in TestResult.all() if result.test == self )

    @property
    def subjects(self):
        """ Return a generator for all of the valid subjects """
        return (subject for subject in self.subject_type.all() if kimapi.valid_match(self,subject) )

    def result_with_subject(self, subject):
        """ Get the first result with the model: model, or None """
        try:
            return next( result for result in self.results if result.model == model )
        except StopIteration:
            raise PipelineDataMissing, "Could not find a TestResult for ({}, {})".format(self,model)

    def processed_infile(self,subject):
        """ Process the input file, with template, and return a file object to the result """
        template.process(self.infile,subject,self)
        return open(os.path.join(self.path,TEMP_INPUT_FILE))

    def subjectname_processed_infile(self,subject):
        template.process(self.infile, subject, self, modelonly=True)
        return open(os.path.join(self.path, TEMP_INPUT_FILE))

    @property
    def template(self):
        return template_environment.get_template(os.path.join(self.path, TEMPLATE_FILE))



class Subject(KIMObject):
    """ A subject, something that gets
    run against, usually a model """
    makeable = True

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Model, with a kim_code """
        super(Subject,self).__init__(kim_code,*args,**kwargs)

    @property
    def results(self):
        """ Get a generator of all of the results for this model """
        return ( result for result in TestResult.all() if result.model == self )

    @property
    def runners(self):
        """ Return a generator of the valid matching tests that match this model """
        return ( test for test in Test.all() if kimapi.valid_match(test,self) )


class Result(KIMObject):
    """ A result, either a test result, or a verification result """
    makeable = False

    def __init__(self, kim_code = None, pair = None, results = None, search=True):
        """ Initialize the TestResult.  You can either pass a kim_code as with other KIMObjects, or
            a pair = (test,model) being a test and model object tuple, and try to look up the corresponding match

            the results parameter, if passed will accept either a dictionary or a JSON decodable string, and the resuls
            stored at the corresponding TestResult will be modified.

            So, if you wanted to create a new TestResult with code "TR_012345678901_000"
            with certain results you would::

                results = {"one": 1, "two": 2}
                tr = TestResult("TR_012345678901_000",results=results,search=False)

            setting search to false is required if a test result without the passed kim_code doesn't yet exist

            To find a test result for the test "TE_000000000000_000" and model "MO_000000000000_000" you would::

                tr = TestResult(pair=(Test("TE_000000000000_000"), Model("MO_000000000000_000")))
        """
        if pair and kim_code:
            raise SyntaxWarning, "TestResult should have a pair, or a kim_code or neither, not both"

        if pair:
            test, model = pair
            result = test.result_with_model(model)
            kim_code = result.kim_code

        else:
            if not kim_code:
                kim_code = new_test_result_id()
                search = False

        super(Result,self).__init__(kim_code,search=search)

        if not self.exists and not search:
            #If this TR doesn't exist and we have search off, create it
            self.create_dir()

        self.results = PersistentDict(os.path.join(self.path,self.kim_code),format='yaml')
        #if we recieved a json string, write it out
        if results:
            logger.debug("Recieved results, writing out to %r", self.kim_code)

            if isinstance(results,dict):
                #we have a dict
                incoming_results = results
            else:
                #if it is a json string try to convert it
                try:
                    incoming_results = simplejson.loads(results)
                except TypeError:
                    #wasn't convertable
                    raise PipelineResultsError, "Could not understand the format of the results: {}".format(results)

            #also move all of the files
            ### FIXME FIXME added these two lines, they're dumb
            self.results.update(incoming_results)
            incoming_results = self.results

            testname = incoming_results["test-extended-id"]

            files = template.files_from_results(incoming_results)
            if files:
                logger.debug("found files to move")
                testdir = Test(testname).path
                for src in files:
                    logger.debug("copying %r over", src)
                    shutil.copy(os.path.join(testdir,src),self.path)

            self.results.update(incoming_results)
            self.results.sync()
            logger.info("Results created in %r", self.kim_code)

        try:
            self.test = Test(self.results["test-extended-id"])
        except KeyError:
            self.test = None
        try:
            self.model = Model(self.results["model-extended-id"])
        except KeyError:
            self.model = None

    def sync(self):
        """ sync not only the info file but also the results """
        self.results.sync()

    @property
    def files(self):
        """ A list of all of the files in the test_result from the @FILE directive """
        return map(os.path.basename,template.files_from_results(self.results))

    @property
    def full_file_paths(self):
        """ generator of files from the @FILE directive with a full path """
        return ( os.path.join(self.path, filename) for filename in self.files )

    @property
    def file_handlers(self):
        """ return a generator of file handlers for all of the files """
        return ( open(filename) for filename in self.full_file_paths )

    def _is_property(self,key):
        """ Tells whether a key is a property or not """
        return bool(re.match(database.RE_KIMID, key))

    @property
    def property_codes(self):
        """ Return a generator of all property kim_codes computed in this test result """
        return ( x for x in filter(self._is_property, self.results.keys() ) )

    def __getitem__(self,key):
        """ Make it so that results behave like their result dictionary for access """
        return self.results.__getitem__(key)

    #def __getattr__(self,attr):
    #    """ if we didn't find the attr, look in self.results for the attr,

    #        This magic allows the result object to behave like its result dictionary magically
    #    """
    #    self.info = PersistentDict(os.path.join(self.path,METADATA_INFO_FILE))
    #    return self.results.__getattribute__(attr)

    @property
    def keys(self):
        return self.results.keys()

    @property
    def values(self):
        return self.results.values()

    @classmethod
    def result_exists(cls,runner,subject):
        """ Check to see if the test result exists for a (test,model) pair """
        try:
            cls(pair=(runner,subject))
        except PipelineDataMissing:
            return False
        return True

    @classmethod
    def duplicates(cls):
        """ Return a generator of all of the duplicated results,
        duplication meaning the exact same (test,model) pairs """
        pairs = set()
        for result in cls.all():
            pair = (result.runner, result.subject)
            if pair in pairs:
                yield result
            else:
                pairs.add(pair)


#===========================================
# Result Objs
#===========================================


#-------------------------------------
# TestResult
#-------------------------------------
class TestResult(Result):
    """ A test result, KIMObject with
    """
    required_leader = "TR"
    makeable = False

    def __init__(self, kim_code = None,*args,**kwargs):
        """ Naked initialization """
        super(TestResult,self).__init__(kim_code,*args,**kwargs)

#------------------------------------------
# VerificationResult
#------------------------------------------
class VerificationResult(KIMObject):
    """ A verification result, KIMObject with
    """
    required_leader = "VR"
    makeable = False

    def __init__(self, kim_code = None, *args, **kwargs):
        """ Naked initialization """
        super(VerificationResult,self).__init__(kim_code,*args,**kwargs)

#------------------------------------------
# ReferenceDatum
#------------------------------------------
class ReferenceDatum(KIMObject):
    """ a piece of reference data, a KIMObject with:

        Settings:
            required_leader = "RD"
            makeable = False

        .. todo::

            Not really implemented!

    """
    required_leader = "RD"
    makeable = False

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the ReferenceDatum, with a kim_code """
        super(ReferenceDatum,self).__init__(kim_code,*args,**kwargs)

#===============================================
# Subject Objs
#==============================================

#--------------------------------------
# Model
#-------------------------------------
class Model(Subject):
    """ A KIM Model, KIMObject with

        Settings:
            required_leader = "MO"
            makeable = True
    """
    required_leader = "MO"
    makeable = True

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Model, with a kim_code """
        super(Model,self).__init__(kim_code,*args,**kwargs)

    @property
    def model_driver(self):
        """ Return the model driver if there is one, otherwise None,
            currently, this tries to parse the kim file for the MODEL_DRIVER_NAME line
        """
        try:
            return ModelDriver(next( line.split(":=")[1].strip() for line in self.makefile if line.startswith("MODEL_DRIVER_NAME") ))
        except StopIteration:
            return None

    @property
    def results(self):
        """ Get a generator of all of the results for this model """
        return ( result for result in TestResult.all() if result.model == self )

    @property
    def tests(self):
        """ Return a generator of the valid matching tests that match this model """
        return ( test for test in Test.all() if kimapi.valid_match(test,self) )


#=============================================
# Runner Objs
#=============================================

#---------------------------------------------
# Test
#---------------------------------------------
class Test(Runner):
    """ A kim test, it is a KIMObject, plus

        Settings:
            required_leader = "TE"
            makeable = True

        Attributes:
            executable
                a path to its executable
            outfile_path
                path to its INPUT_FILE
            infile_path
                path to its OUTPUT_FILE
            out_dict
                a dictionary of its output file, mapping strings to
                Property objects
    """
    required_leader = "TE"
    makeable = True
    result_type = TestResult
    subject_type = Model

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(Test,self).__init__(kim_code,*args,**kwargs)


    @property
    def _reversed_out_dict(self):
        """ Reverses the out_dict """
        return { value:key for key,value in self.out_dict.iteritems() }

    @property
    def test_drivers(self):
        """ Return a generator of test drivers this guy relies on """
        return ( depend for depend in self.dependencies if depend.required_leader == "TD")

    def result_with_model(self, model):
        """ Get the first result with the model: model, or None """
        return self.result_with_subject(model)

    def modelname_processed_infile(self, model):
        return self.subjectname_processed_infile(model)

    @property
    def models(self):
        """ Returns a generator of valid matched models """
        return self.subjects


#------------------------------------------
# VerificationTest(Check)
#------------------------------------------
class VerificationTest(Runner):
    """ A kim test, it is a KIMObject, plus

        Settings:
            required_leader = "VT"
            makeable = True

        Attributes:
            executable
                a path to its executable
            outfile_path
                path to its INPUT_FILE
            infile_path
                path to its OUTPUT_FILE
            out_dict
                a dictionary of its output file, mapping strings to
                Property objects
    """
    required_leader = "VT"
    subject_type = Test
    result_type = VerificationResult

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(VerificationTest,self).__init__(kim_code,*args,**kwargs)

    @property
    def _reversed_out_dict(self):
        """ Reverses the out_dict """
        return { value:key for key,value in self.out_dict.iteritems() }


#------------------------------------------
# VerificationModel(Check)
#------------------------------------------
class VerificationModel(KIMObject):
    """ A kim test, it is a KIMObject, plus

        Settings:
            required_leader = "VM"
            makeable = True

        Attributes:
            executable
                a path to its executable
            outfile_path
                path to its INPUT_FILE
            infile_path
                path to its OUTPUT_FILE
            out_dict
                a dictionary of its output file, mapping strings to
                Property objects
    """
    required_leader = "VM"
    makeable = True

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(VerificationModel,self).__init__(kim_code,*args,**kwargs)
        self.executable = os.path.join(self.path,self.kim_code)
        # self.outfile_path = os.path.join(self.path,OUTPUT_FILE)
        self.infile_path = os.path.join(self.path,INPUT_FILE)
        # self.out_dict = self._outfile_to_dict()

    def __call__(self,*args,**kwargs):
        """ Calling a test object executes its executable in its own directory
            args and kwargs are passed to ``subprocess.check_call`` """
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)




#==========================================
# Drivers
#===========================================

#------------------------------------------
# TestDriver
#------------------------------------------
class TestDriver(KIMObject):
    """ A test driver, a KIMObject with,

        Settings:
            required_leader = "TD"
            makeable = True

        Attributes:
            executable
                the executable for the TestDriver
    """
    required_leader = "TD"
    makeable = True

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the TestDriver, with a kim_code """
        super(TestDriver,self).__init__(kim_code,*args,**kwargs)
        self.executable = os.path.join(self.path, self.kim_code)

    def __call__(self,*args,**kwargs):
        """ Make the TestDriver callable, executing its executable in its own directory,
            passing args and kwargs to ``subprocess.check_call``
        """
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)

    @property
    def tests(self):
        """ Return a generator of all tests using this TestDriver """
        return ( test for test in Test.all() if self in test.test_drivers )


#------------------------------------------
# ModelDriver
#------------------------------------------
class ModelDriver(KIMObject):
    """ A model driver, a KIMObject with,

        Settings:
            required_leader = "MD"
            makeable = True
    """
    required_leader = "MD"
    makeable = True

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the ModelDriver, with a kim_code """
        super(ModelDriver,self).__init__(kim_code,*args,**kwargs)

    @property
    def models(self):
        """ Return a generator of all of the models using this model driver """
        return ( model for model in Model.all() if self==model.model_driver )

#------------------------------------------
# VirtualMachine
#------------------------------------------
class VirtualMachine(KIMObject):
    """ for a virtual machine, a KIMObject with:

        Settings:
            required_leader = "VM"
            makeable = False
    """
    required_leader = "VM"
    makeable = False

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize a VirtualMachine with a kim_code """
        super(VirtualMachine,self).__init__(kim_code,*args,**kwargs)

#--------------------------------------------
# Helper code
#--------------------------------------------
def new_tr_kimid():
    """ Generate a new Test Result kimid """
    existing = set( result.kim_code for result in TestResult.all() )
    kim_code = database.format_kim_code(None,"TR","{:012d}".format(database.randint()),"000")
    while kim_code in existing:
        kim_code = database.format_kim_code(None,"TR","{:012d}".format(database.randint()),"000")
    return kim_code

def new_vr_kimid():
    """ Generate a new Test Result kimid """
    existing = set( result.kim_code for result in VerificationResult.all() )
    kim_code = database.format_kim_code(None,"VR","{:012d}".format(database.randint()),"000")
    while kim_code in existing:
        kim_code = database.format_kim_code(None,"VR","{:012d}".format(database.randint()),"000")
    return kim_code

def new_test_result_id(number=None):
    """ Generate or get a new test result id, currently make them up, eventually request them from the website """
    if number:
        version = database.get_new_version(None,"TR",number)
        return database.format_kim_code(None,"TR",number,version)
    else:
        kim_code = new_tr_kimid()
        logger.info("Generated new TR kim_code: %r", kim_code)
        return kim_code

def new_verification_result_id(number=None):
    """ Generate or get a new verification result id, currently make them up, eventually request them from the website """
    if number:
        version = database.get_new_version(None,"VR",number)
        return database.format_kim_code(None,"VR",number,version)
    else:
        kim_code = new_vr_kimid()
        logger.info("Generated new VR kim_code: %r", kim_code)
        return kim_code

def randint():
    """ Return a random kim integer """
    return random.randint(0,1e12)

# two letter codes to the associated class
code_to_model = {"TE": Test, "MO": Model, "TD": TestDriver, "TR": TestResult ,
    "VT": VerificationTest, "VM": VerificationModel, "VR": VerificationResult,
    "RD": ReferenceDatum,  "MD": ModelDriver }

def kim_obj(kim_code, *args, **kwargs):
    """ Just given a kim_code try to make the right object, i.e. try to make a TE code a Test, etc. """
    name,leader,num,version = database.parse_kim_code(kim_code)
    cls = code_to_model.get(leader, KIMObject)
    return cls(kim_code, *args, **kwargs)

