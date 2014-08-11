"""
@@.. module:: models
    :synopsis: Holds the python object models for kim objects

.. moduleauthor:: Alex Alemi <alexalemi@gmail.com>

A pure python object wrapper for the pipeline stuff

Has a base ``KIMObject`` class and

 * Test
 * Model
 * TestDriver
 * ModelDriver
 * TestVerification
 * ModelVerification
 * VirtualMachine

classes, all of which inherit from ``KIMObject`` and aim to know how to handle themselves.

"""
from template import template_environment
import database
import kimapi
from config import *
from config import __kim_api_version_spec__
from logger import logging
logger = logging.getLogger("pipeline").getChild("kimobjects")

from packaging import version
from contextlib import contextmanager
import template
import shutil
import subprocess
import re
import dircache
import simplejson
import glob

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

    def __init__(self,kim_code,search=True,subdir=None,strict=False):
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
                subdir (str)
                    In order to point to a directory that does not follow that pattern
                    /home/openkim/openkim-repository/{mo,md,te...}/KIM_CODE/KIM_CODE
                    can provide the folder of
                    /home/openkim/openkim-repository/{mo,md,te...}/SUBDIR/KIM_CODE
                strict (bool)
                    Allow non-standard kimcode names to go through the kimobjects interface
                    If True, then allowed, otherwise only allow strict KIM IDs
        """
        logger.debug("Initializing a new KIMObject: %r", kim_code)
        self.isdebugid = False

        try:
            name, leader, num, version = database.parse_kim_code(kim_code)
        except InvalidKIMID as e:
            if not strict:
                name, leader, num, version = database.get_debug_extended_id(kim_code)
                self.isdebugid = True
            else:
                raise e

        # test to see if we have the right leader
        if self.required_leader:
            assert leader==self.required_leader,"{} not a valid KIM code for {}".format(kim_code, self.__class__.__name__)

        #grab the attributes
        self.kim_code_name = name
        self.kim_code_leader = leader
        self.kim_code_number = num
        self.kim_code_version = version

        if not search or self.isdebugid:
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

        if not self.isdebugid:
            self.kim_code_id = database.strip_name(self.kim_code)
            self.kim_code_short = database.strip_version(self.kim_code)
        else:
            self.kim_code_id = self.kim_code_number
            self.kim_code_short = self.kim_code
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
    def kimfile_name(self):
        postfix = ''
        with self.in_dir():
            if os.path.exists(DOTKIM_FILE):
                postfix = DOTKIM_FILE
            else:
                ll = glob.glob("*.kim")
                if len(ll):
                    postfix = ll[0]
        if postfix:
            return os.path.join(self.path, postfix)
        else:
            raise IOError(".kim file not found for %r" % self)

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

    @property
    def drivers(self):
        return ()

    def make(self):
        """ Try to build the thing, by executing ``make`` in its directory """
        if self.drivers:
            for dr in self.drivers:
                dr.make()

        if self.makeable:
            if not version.Version(self.kim_api_version) in version.Specifier(__kim_api_version_spec__):
                return
            with self.in_dir():
                with open(os.path.join(KIM_LOG_DIR, "make.log"), "a") as log:
                    logger.debug("Attempting to make %r: %r", self.__class__.__name__, self.kim_code)
                    try:
                        subprocess.check_call('make', stdout=log, stderr=log)
                    except Exception as e:
                        raise subprocess.CalledProcessError("Could not build %r" % self, e)
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
        kim_codes = (
            subpath for subpath in dircache.listdir(type_dir) if (
                os.path.isdir(os.path.join(type_dir, subpath))
            )
        )
        for x in kim_codes:
            try:
                yield cls(x)
            except Exception as e:
                logger.exception("Exception on formation of kim_code (%s)", x)

    @property
    def kimspec(self):
        specfile = os.path.join(self.path,CONFIG_FILE)
        if not os.path.exists(specfile):
            return None

        spec = {}
        with open(specfile) as f:
            spec = loadedn(f)
        return spec

    @property
    def kim_api_version(self):
        if self.kimspec:
            return self.kimspec.get("kim-api-version")
        return None

    @property
    def pipeline_api_version(self):
        if self.kimspec:
            return self.kimspec.get("pipeline-api-version")
        return None

    @property
    def dependencies(self):
        """ Return a generator of kim objects that are its dependencies """
        return list(self.drivers)

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
    result_leader = "TR"

    def __init__(self,kim_code,*args,**kwargs):
        super(Runner,self).__init__(kim_code,*args,**kwargs)
        self.executable = os.path.join(self.path,TEST_EXECUTABLE)
        self.infile_path = os.path.join(self.path,INPUT_FILE)
        self.depfile_path = os.path.join(self.path,DEPENDENCY_FILE)

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

    @property
    def depfile(self):
        """ return a file object for DEPENDENCY_FILE """
        if os.path.isfile(self.depfile_path):
            return open(self.depfile_path)
        return None

    @property
    def subjects(self):
        """ Return a generator for all of the valid subjects """
        return (subject for subject in self.subject_type.all() if kimapi.valid_match(self,subject) )

    def processed_infile(self,subject):
        """ Process the input file, with template, and return a file object to the result """
        template.process(self.infile_path,subject,self)
        return open(os.path.join(self.path,TEMP_INPUT_FILE))

    def subjectname_processed_infile(self,subject):
        template.process(self.infile_path, subject, self, modelonly=True)
        return open(os.path.join(self.path, TEMP_INPUT_FILE))

    def runtime_dependencies(self, subject=None):
        """ go ahead and append the subject to single test items """
        if self.depfile:
            raw, out = loadedn(self.depfile), []
            for dep in raw:
                newdep = dep

                if subject and isinstance(dep, basestring):
                    tt = kim_obj(dep)
                    if isinstance(tt, Test):
                        newdep = [str(tt), str(subject)]

                out.append(newdep)
            return out
        return []

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
    def runners(self):
        """ Return a generator of the valid matching tests that match this model """
        return ( test for test in Test.all() if kimapi.valid_match(test,self) )


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
    subject_name = "model"

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Model, with a kim_code """
        super(Model,self).__init__(kim_code,*args,**kwargs)

    @property
    def model_driver(self):
        """ Return the model driver if there is one, otherwise None,
            currently, this tries to parse the kim file for the MODEL_DRIVER_NAME line
        """
        if not self.kimspec or not self.kimspec.get('model-driver'):
            return None 
        else:
            return ModelDriver(self.kimspec['model-driver'])

    @property
    def tests(self):
        """ Return a generator of the valid matching tests that match this model """
        return ( test for test in Test.all() if kimapi.valid_match(test,self) )

    @property
    def drivers(self):
        return [] if not self.model_driver else [self.model_driver]

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
    subject_type = Model
    result_leader = "TR"
    runner_name = "test"
    subject_name = "test"

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
        if not self.kimspec or not self.kimspec.get('test-driver'):
            return None 
        else:
            return TestDriver(self.kimspec['test-driver'])

    def result_with_model(self, model):
        """ Get the first result with the model: model, or None """
        return self.result_with_subject(model)

    def modelname_processed_infile(self, model):
        return self.subjectname_processed_infile(model)

    @property
    def models(self):
        """ Returns a generator of valid matched models """
        return self.subjects

    @property
    def drivers(self):
        return [] if not self.test_drivers else [self.test_drivers]

#------------------------------------------
# TestVerification(Check)
#------------------------------------------
class TestVerification(Test):
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
    required_leader = "TV"
    makeable = True
    subject_type = Test
    result_leader = "VR"
    runner_name = "test-verification"

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(TestVerification,self).__init__(kim_code,*args,**kwargs)


#------------------------------------------
# ModelVerification(Check)
#------------------------------------------
class ModelVerification(Test):
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
    required_leader = "MV"
    makeable = True
    subject_type = Model
    result_leader = "VR"
    runner_name = "model-verification"

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(ModelVerification,self).__init__(kim_code,*args,**kwargs)


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
        self.executable = os.path.join(self.path, TEST_EXECUTABLE)

    def __call__(self,*args,**kwargs):
        """ Make the TestDriver callable, executing its executable in its own directory,
            passing args and kwargs to ``subprocess.check_call``
        """
        with self.in_dir():
            subprocess.check_call(self.executable,*args,**kwargs)

    @property
    def tests(self):
        """ Return a generator of all tests using this TestDriver """
        return ( test for test in Test.all() if self in test.drivers )


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
# two letter codes to the associated class
code_to_model = {"TE": Test, "MO": Model, "TD": TestDriver,
    "TV": TestVerification, "MV": ModelVerification,
     "MD": ModelDriver }

def kim_obj(kim_code, strict=False, *args, **kwargs):
    """ Just given a kim_code try to make the right object, i.e. try to make a TE code a Test, etc. """
    try:
        name,leader,num,version = database.parse_kim_code(kim_code)
    except InvalidKIMID as e:
        if not strict:
            leader = database.get_leader_by_search(kim_code)
        else:
            raise e
    cls = code_to_model.get(leader, KIMObject)
    return cls(kim_code, *args, **kwargs)

