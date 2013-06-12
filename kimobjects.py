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
 * VerificationTest
 * VerificationModel
 * VirtualMachine

classes, all of which inherit from ``KIMObject`` and aim to know how to handle themselves.

"""

from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("kimobjects")

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
        for x in kim_codes:
            try:
                yield cls(x)
            except Exception as e:
                logger.exception("Exception on formation of kim_code (%s)", x)


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
    def subjects(self):
        """ Return a generator for all of the valid subjects """
        return (subject for subject in self.subject_type.all() if kimapi.valid_match(self,subject) )

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
    subject_type = Model
    result_leader = "TR"

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
class VerificationTest(Test):
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
    makeable = True
    subject_type = Test
    result_leader = "VR"

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(VerificationTest,self).__init__(kim_code,*args,**kwargs)


#------------------------------------------
# VerificationModel(Check)
#------------------------------------------
class VerificationModel(Test):
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
    subject_type = Model
    result_leader = "VR"

    def __init__(self,kim_code,*args,**kwargs):
        """ Initialize the Test, with a kim_code """
        super(VerificationModel,self).__init__(kim_code,*args,**kwargs)


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
# two letter codes to the associated class
code_to_model = {"TE": Test, "MO": Model, "TD": TestDriver,
    "VT": VerificationTest, "VM": VerificationModel,
     "MD": ModelDriver }

def kim_obj(kim_code, *args, **kwargs):
    """ Just given a kim_code try to make the right object, i.e. try to make a TE code a Test, etc. """
    name,leader,num,version = database.parse_kim_code(kim_code)
    cls = code_to_model.get(leader, KIMObject)
    return cls(kim_code, *args, **kwargs)

