"""
Methods that deal with the KIM API directly.  Currently these are methods
that build the libraries and use the Python interface kimservice
to test if tests and models match.
"""
import os
from subprocess import check_output, check_call, CalledProcessError
from contextlib import contextmanager
from packaging import version
from functools import partial

import config as cf
from config import __pipeline_version_spec__, __kim_api_version_spec__
from logger import logging
logger = logging.getLogger("pipeline").getChild("kimapi")

#======================================
# API build utilities
#======================================
MAKE_LOG = os.path.join(cf.LOG_DIR, "make.log")

@contextmanager
def in_dir(path):
    cwd = os.getcwd()
    os.chdir(path)
    try:
        yield
    except Exception as e:
        raise e
    finally:
        os.chdir(cwd)

def make_config():
    with open(os.path.join(cf.KIM_REPOSITORY_DIR, "md", "Makefile.KIM_Config"), 'w') as f:
        check_call(["kim-api-build-config", "--makefile-kim-config"], stdout=f)
    with open(os.path.join(cf.KIM_REPOSITORY_DIR, "mo", "Makefile.KIM_Config"), 'w') as f:
        check_call(["kim-api-build-config", "--makefile-kim-config"], stdout=f)

def make_all():
    logger.debug("Building everything...")
    make_config()

    import kimobjects
    for o in kimobjects.TestDriver.all():
        o.make()
    for o in kimobjects.Test.all():
        o.make()
    for o in kimobjects.ModelDriver.all():
        o.make()
    for o in kimobjects.Model.all():
        o.make()

def make_object(obj):
    if (not version.Version(obj.kim_api_version)
            in version.Specifier(__kim_api_version_spec__)):
        logger.debug("KIM API version does not match object's, skipping build")
        return

    with obj.in_dir():
        with open(MAKE_LOG, 'a') as log:
            try:
                check_call(['make'], stdout=log, stderr=log)
            except CalledProcessError as e:
                raise cf.KIMBuildError("Could not build %r, check %s" % (obj, MAKE_LOG))


#======================================
# Some kim api wrapped things
#======================================
import kimservice

def valid_match_util(test,model):
    """ Check to see if a test and model mach by using Ryan's utility """
    logger.debug("invoking Ryan's utility for (%r,%r)",test,model)
    test_dotkim = os.path.join(test.path, cf.DOTKIM_FILE)
    model_dotkim = os.path.join(model.path, cf.DOTKIM_FILE)
    out = check_output([cf.KIM_API_CHECK_MATCH_UTIL,test_dotkim,model_dotkim])
    if out == "MATCH\n":
        return True
    return False


def valid_match_codes(test,model):
    """ Test to see if a test and model match using the kim API, returns bool

        Tests through ``kimservice.KIM_API_init``, running in its own forked process
    """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    logger.debug("invoking KIMAPI for (%r,%r)",test,model)
    pid = os.fork()
    if (pid==0):
        logger.debug("in fork")
        match, pkim = kimservice.KIM_API_file_init(str(test.kimfile_name), str(model))
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
        raise cf.KIMRuntimeError
        match = False

    if match:
        return True
    else:
        return False

def valid_match(test,model):
    """ Test to see if a test and model match using the kim API, returns bool

        Tests through ``kimservice.KIM_API_init``, running in its own forked process
    """
    ver = version.Version
    ver_pipspec = version.Specifier(__pipeline_version_spec__)
    ver_kimspec = version.Specifier(__kim_api_version_spec__)

    version_match = (
        ver(test.kim_api_version) in ver_kimspec and
        ver(model.kim_api_version) in ver_kimspec and
        ver(test.pipeline_api_version) in ver_pipspec
    )

    logger.debug("Checking match for (%r, %r), version match %r" % (test,model,version_match))
    return version_match and valid_match_codes(test, model)
