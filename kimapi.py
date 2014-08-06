"""
Methods that deal with the KIM API directly.  Currently these are methods
that build the libraries and use the Python interface kimservice
to test if tests and models match.
"""
from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("kimapi")

from subprocess import check_output, check_call
from contextlib import contextmanager

#======================================
# API build utilities
#======================================
MAKE_LOG = os.path.join(KIM_LOG_DIR, "make.log")

@contextmanager
def in_api_dir():
    cwd = os.getcwd()
    os.chdir(KIM_API_DIR)
    try:
        yield
    except Exception as e:
        raise e
    finally:
        os.chdir(cwd)

def make_all():
    logger.debug("Building everything...")
    with in_api_dir():
        with open(MAKE_LOG, "a") as log:
            check_call(["make", "clean"], stdout=log, stderr=log)
            check_call(["make"], stdout=log, stderr=log)

def make_api():
    logger.debug("Building the API...")
    with in_api_dir():
        with open(MAKE_LOG, "a") as log:
            check_call(["make", "kim-api-clean"], stdout=log, stderr=log)
            check_call(["make", "config"], stdout=log, stderr=log)
            check_call(["make", "kim-api-libs"], stdout=log, stderr=log)

#======================================
# Some kim api wrapped things
#======================================
try:
    import kimservice
except ImportError as e:
    make_api()
    import kimservice

def valid_match_util(test,model):
    """ Check to see if a test and model mach by using Ryan's utility """
    logger.debug("invoking Ryan's utility for (%r,%r)",test,model)
    test_dotkim = os.path.join(test.path, DOTKIM_FILE)
    model_dotkim = os.path.join(model.path, DOTKIM_FILE)
    out = check_output([KIM_API_CHECK_MATCH_UTIL,test_dotkim,model_dotkim])
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
        raise KIMRuntimeError
        match = False

    if match:
        return True
    else:
        return False

def valid_match(test,model):
    """ Test to see if a test and model match using the kim API, returns bool

        Tests through ``kimservice.KIM_API_init``, running in its own forked process
    """
    return valid_match_codes(test, model)
