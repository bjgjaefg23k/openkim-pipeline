""" This should contain some nice functions and methods for dealing
with the repository structure """

import os, sys
import kimservice
from config import *
logger = logger.getChild("repository")

#======================================
# Some kim api wrapped things
#======================================

def valid_match(test,model,force=False):
    """ Test to see if a test and model match using the kim API, returns bool """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    logger.debug("invoking KIMAPI for (%r,%r)",test,model)
    pid = os.fork()
    if (pid==0):
        logger.debug("in fork")
        match, pkim = kimservice.KIM_API_init(test.kim_code,model.kim_code)
        if match:
            kimservice.KIM_API_free(pkim)
            sys.exit(0)
        sys.exit(1)

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


