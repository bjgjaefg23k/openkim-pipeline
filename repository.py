""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess, simplejson, shutil
from contextlib import contextmanager
import kimservice, kimid
from persistentdict import PersistentDict, PersistentDefaultDict
from config import *
from subprocess import check_call
import template

logger = logger.getChild("repository")

#======================================
# Some kim api wrapped things
#======================================

def valid_match(testname,modelname,force=False):
    """ Test to see if a test and model match using the kim API, returns bool """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    if testname not in KIM_TESTS:
        logger.error("test %r not valid",testname)
        raise PipelineFileMissing, "test {} not valid".format(testname)
    if modelname not in KIM_MODELS:
        logger.error("model %r not valid", modelname)
        raise PipelineFileMissing, "model {} not valid".format(modelname)

    with PersistentDict(MATCH_STORE) as store:
        if str((testname,modelname)) in store and not force:
            return store[str((testname,modelname))]

        logger.debug("invoking KIMAPI for (%r,%r)",testname,modelname)
        pid = os.fork()
        if (pid==0):
            logger.debug("in fork")
            match, pkim = kimservice.KIM_API_init(testname,modelname)
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
            logger.error("We seem to have a Kim init error on (%r,%r)", testname, modelname)
            #raise KIMRuntimeError
            match = False

        if match:
            logger.debug("freeing KIMAPI")
            #kimservice.KIM_API_free(pkim)
            store[str((testname,modelname))] = True
            return True
        else:
            store[str((testname,modelname))] = False
            return False

#==========================================
# Results in repo
#==========================================

def files_from_results(results):
    """ Given a dictionary of results,
    return the filenames for any files contained in the results """
    logger.debug("parsing results for file directives")
    testname = results["_testname"]
    testdir = test_dir(testname)
    #get only those files that match the file directive, needs strings to process
    files = filter(None,(template.get_file(str(val),testdir) for key,val in results.iteritems()))
    return files


def write_result_to_file(results, tr_id, pk=None):
    """ Given a dictionary of results, write it to the corresponding file, or create a new id

        This assumes the results already have the proper output Property IDs
        Write the property json file in its corresponding location
        and copy any files associated with it

        Also, update the property store for fast lookups

    """
    logger.info("writing result file for results: %r",results)
    testname = results["_testname"]
    modelname = results["_modelname"]

    if tr_id == None:
        tr_id = kimid.new_kimid("TR")
        logger.debug("Making a TR ID up... %r", tr_id)
    outputfolder = tr_id
    outputfilename = outputfolder
    outputpath = os.path.join(outputfolder,outputfilename)

    with in_repo_dir(KIM_TEST_RESULTS_DIR):
        os.mkdir(outputfolder)
        with open(outputpath,"w") as fobj:
            simplejson.dump(results,fobj)

        #copy any corresponding files to the test results directory
        files = files_from_results(results)
        if files:
            logger.debug("found files to move")
            testdir = test_dir(testname)
            for src in files:
                logger.debug("copying %r over", src)
                shutil.copy(os.path.join(testdir,src),outputfolder)

        #make symlinks
        #os.symlink(test_dir(testname),os.path.join(outputfolder,testname))
        #os.symlink(model_dir(modelname),os.path.join(outputfolder,modelname))

    with test_result_store() as store:
        logger.debug("updating test result store")
        store[testname][modelname] = tr_id

    print "Wrote results in: {}".format(outputfilename)



#==========================================
# Processor helper files
#==========================================


