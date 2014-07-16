"""
Set of methods for querying the database in one form or the other

As well as parsing and handling kim_codes

Currently these calls mostly glob on the database, could be replaced by something more elegant later

"""
from config import *
import kimservice

from logger import logging
logger = logging.getLogger("pipeline").getChild("kimapi")

from subprocess import check_output

#======================================
# Some kim api wrapped things
#======================================

def valid_match_util(test,model):
    """ Check to see if a test and model mach by using Ryan's utility """
    logger.debug("invoking Ryan's utility for (%r,%r)",test,model)
    test_dotkim = os.path.join(test.path, DOTKIM_FILE)
    model_dotkim = os.path.join(model.path, DOTKIM_FILE)
    out = check_output([KIM_API_CHECK_MATCH_UTIL,test_dotkim,model_dotkim])
    if out == "MATCH\n":
        return True
    return False


def valid_match_codes(test_code,model_code):
    """ Test to see if a test and model match using the kim API, returns bool

        Tests through ``kimservice.KIM_API_init``, running in its own forked process
    """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    logger.debug("invoking KIMAPI for (%r,%r)",test_code,model_code)
    pid = os.fork()
    if (pid==0):
        logger.debug("in fork")
        match, pkim = kimservice.KIM_API_init(test_code,model_code)
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
        logger.error("We seem to have a Kim init error on (%r,%r)", test_code, model_code)
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
    return valid_match_codes(test.kim_code,model.kim_code)
