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
#============================
# Silly git stuff
#============================

@contextmanager
def in_repo_dir(dir=None):
    """Change to repo directory to execute code, then change back"""
    cwd = os.getcwd()
    os.chdir(dir or KIM_REPOSITORY_DIR)
    logger.debug("moved to dir: {}".format(os.getcwd()))
    yield
    os.chdir(cwd)

def pull(remote='origin',branch='master'):
    """ do a git pull """
    logger.info("doing a git pull")
    with in_repo_dir():
        return subprocess.call(['git','pull',remote,branch])

def status():
    """ get git status"""
    with in_repo_dir():
        return subprocess.call(['git','status'])

def add():
    """ do a git add """
    logger.info("doing a git add")
    with in_repo_dir():
        return subprocess.call(['git','add','.'])

def commit(mesg=''):
    logger.info("doing a git commit")
    with in_repo_dir():
        return subprocess.call(['git','commit','-a','--allow-empty-message','-m',mesg])

def push(remote='origin',branch='master'):
    """ do a git push """
    logger.info("doing a git push")
    with in_repo_dir():
        return subprocess.call(['git','push',remote,branch])

def update(mesg="",remote='origin',branch='master'):
    """ update the repo with an add commit and push """
    logger.info("doing a git update")
    add()
    commit(mesg)
    push(remote,branch)

#======================================
# Some kim api wrapped things
#======================================

def valid_match(testname,modelname):
    """ Test to see if a test and model match using the kim API, returns bool """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    if testname not in KIM_TESTS:
        logger.error("test %r not valid",testname)
        raise PipelineFileMissing, "test {} not valid".format(testname)
    if modelname not in KIM_MODELS:
        logger.error("model %r not valid", modelname)
        raise PipelineFileMissing, "model {} not valid".format(modelname)
    
    with PersistentDict(MATCH_STORE) as store:
        if str((testname,modelname)) in store:
            return store[str((testname,modelname))]

        logger.debug("invoking KIMAPI for (%r,%r)",testname,modelname)
        match, pkim = kimservice.KIM_API_init(testname,modelname)
        if match:
            logger.debug("freeing KIMAPI")
            kimservice.KIM_API_free(pkim)
            store[str((testname,modelname))] = True
            return True
        else:
            store[str((testname,modelname))] = False
            return False

def tests_for_model(modelname):
    """ Return a generator of all valid tests for a model """
    logger.debug("all tests for model %r",modelname)
    return (test for test in KIM_TESTS if valid_match(test,modelname) )

def models_for_test(testname):
    """ Return a generator of all valid models for a test """
    logger.debug("all models for test %r",testname)
    return (model for model in KIM_MODELS if valid_match(testname,model) )

def test_executable(testname):
    """ get the executable for a test """
    logger.debug("getting executable for %r",testname)
    return os.path.join(test_dir(testname),testname)

def test_dir(testname):
    """ Get the directory of corresponding testname """
    logger.debug("getting dir for test %r",testname)
    return os.path.join(KIM_TESTS_DIR,testname)

def model_dir(modelname):
    """ Get the model directory given model name """
    logger.debug("getting dir for model %r",modelname)
    return os.path.join(KIM_MODELS_DIR,modelname)

def model_driver_dir(modeldrivername):
    """ Get the model driver directory """
    logger.debug("getting dir for model driver %r",modeldrivername)
    return os.path.join(KIM_MODEL_DRIVERS_DIR,modeldrivername)

def test_driver_dir(testdrivername):
    """ Get the test driver directory """
    logger.debug("getting dir for test driver %r",testdrivername)
    return os.path.join(KIM_TEST_DRIVERS_DIR,testdrivername)

def test_driver_executable(testdrivername):
    """ Get the test driver executable """
    logger.debug("getting exec for test driver %r", testdrivername)
    return os.path.join(test_driver_dir(testdrivername),testdrivername)

def reference_data_dir(referencedataname):
    """ Get the reference data directory """
    logger.debug("getting dir for RD %r",referencedataname)
    return os.path.join(KIM_REFERENCE_DATA_DIR,referencedataname)

def test_result_dir(testresultname):
    """ Get the test result directory """
    logger.debug("getting dir for TR %r",testresultname)
    return os.path.join(KIM_TEST_RESULTS_DIR,testresultname)

def test_result_file(testresultname):
    """ Get the test result file """
    logger.debug("getting file for TR %r",testresultname)
    return os.path.join(test_result_dir(testresultname), testresultname)

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
        

def write_result_to_file(results, pk=None):
    """ Given a dictionary of results, write it to the corresponding file, or create a new id
        
        This assumes the results already have the proper output Property IDs
        Write the property json file in its corresponding location
        and copy any files associated with it

        Also, update the property store for fast lookups
    
    """
    logger.info("writing result file for results: %r",results)
    testname = results["_testname"]
    modelname = results["_modelname"]
    
    tr_id = kimid.new_kimid("TR")
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


def test_result_exists(testname,modelname):
    logger.debug("seeing if test result exists for %r, %r",testname,modelname)
    with test_result_store() as store:
        if testname in store:
            if modelname in store[testname]:
                return True
    return False

def load_info_file(filename):
    """ load a kim json pipeline info file """
    logger.debug("loading info file for %r",filename)
    with open(filename) as fl:
        info = simplejson.load(fl)
    return info

def write_info_file_at(directory,info):
    """ write the dictionary to the corresponding directory """
    logger.debug("writing info file %r at %r",info,directory)
    filepath = os.path.join(directory,PIPELINE_INFO_FILE)
    with open(filepath, "w") as fl:
        simplejson.dump(info,fl)

def persistent_info_file(filename,*args,**kwargs):
    logger.debug("requested persistent info file")
    return PersistentDict(filename,*args,format="json",**kwargs)

def test_info(testname,*args,**kwargs):
    """ load the info file for the corresponding test """
    logger.debug("requested test info for %r",testname)
    location = os.path.join(test_dir(testname), PIPELINE_INFO_FILE)
    return persistent_info_file(location,*args,**kwargs)

def model_info(modelname, *args, **kwargs):
    """ load the info file for the corresponding model """
    logger.debug("requested model info for %r",modelname)
    location = os.path.join(model_dir(modelname), PIPELINE_INFO_FILE)
    return persistent_info_file(location,*args,**kwargs)

def test_result_store():
    """ return the test result store """
    logger.debug("loading test result store")
    return PersistentDefaultDict(TEST_RESULT_STORE)

def test_result_info(tr):
    logger.debug("requested tr info for %r",tr)
    trpath = test_result_file(tr)
    return load_info_file(trpath)


#==========================================
# Processor helper files
#==========================================

def get_path(kid):
    """ Given a kimid give the path to the corresponding place """
    leader,pk,version = kimid.parse_kimid(kid)
    logger.debug("someone requested path for %r",kid)

    if leader=="TE":
        return test_executable(kid)
    if leader=="MO":
        return model_dir(kid)
    if leader=="MD":
        return model_driver_dir(kid)
    if leader=="TD":
        return test_driver_executable(kid)
    if leader=="RD":
        return reference_data_dir(kid)
    if leader=="TR":
        return test_result_dir(kid)
    raise PipelineFileMissing, "don't understand kid: {}".format(kid)


def data_from_rd(rd):
    """ Get the data for the rd id """


def data_from_tr_pr(tr,pr):
    """ Get data from a tr id and pr id """
    logger.debug("getting data for %r,%r",tr,pr)
    info = test_result_info(tr)
    return info[pr]


def data_from_te_mo_pr(te,mo,pr):
    """ Get data from a te, mo, pr """
    logger.debug("getting data for %r,%r,%r",te,mo,pr)
    with test_result_store() as store:
        tr = store[te][mo]
    return data_from_tr_pr(tr,pr)

#===========================================
# rsync utilities
#===========================================

def rsync_update():
    logger.info("attempting rsync")
    check_call("rsync -avz -e ssh {}@{}:{} {}".format(GLOBAL_USER,GLOBAL_HOST,GLOBAL_DIR,GLOBAL_DIR))

def test_model_to_priority(test, model):
    return 1
