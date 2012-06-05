""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess, simplejson, shutil
from contextlib import contextmanager
import kimservice, kimid
from persistentdict import PersistentDict, PersistentDefaultDict
from config import *
from subprocess import check_call

#============================
# Silly git stuff
#============================

@contextmanager
def in_repo_dir(dir=None):
    """Change to repo directory to execute code, then change back"""
    cwd = os.getcwd()
    os.chdir(dir or KIM_REPOSITORY_DIR)
    yield
    os.chdir(cwd)

def pull(remote='origin',branch='master'):
    """ do a git pull """
    with in_repo_dir():
        return subprocess.call(['git','pull',remote,branch])

def status():
    """ get git status"""
    with in_repo_dir():
        return subprocess.call(['git','status'])

def add():
    """ do a git add """
    with in_repo_dir():
        return subprocess.call(['git','add','.'])

def commit(mesg=''):
    with in_repo_dir():
        return subprocess.call(['git','commit','-a','--allow-empty-message','-m',mesg])

def push(remote='origin',branch='master'):
    """ do a git push """
    with in_repo_dir():
        return subprocess.call(['git','push',remote,branch])

def update(mesg="",remote='origin',branch='master'):
    """ update the repo with an add commit and push """
    add()
    commit(mesg)
    push(remote,branch)

#======================================
# Some kim api wrapped things
#======================================

def valid_match(testname,modelname):
    """ Test to see if a test and model match using the kim API, returns bool """
    if testname not in KIM_TESTS:
        raise KeyError, "test {} not valid".format(testname)
    if modelname not in KIM_MODELS:
        raise KeyError, "model {} not valid".format(modelname)
    match, pkim = kimservice.KIM_API_init(testname,modelname)
    if match:
        kimservice.KIM_API_free(pkim)
        return True
    else:
        return False

def tests_for_model(modelname):
    """ Return a generator of all valid tests for a model """
    return (test for test in KIM_TESTS if valid_match(test,modelname) )

def models_for_test(testname):
    """ Return a generator of all valid models for a test """
    return (model for model in KIM_MODELS if valid_match(testname,model) )

def test_executable(testname):
    """ get the executable for a test """
    return os.path.join(test_dir(testname),testname)

def test_dir(testname):
    """ Get the directory of corresponding testname """
    return os.path.join(KIM_TESTS_DIR,testname)

def model_dir(modelname):
    """ Get the model directory given model name """
    return os.path.join(KIM_MODELS_DIR,modelname)

def model_driver_dir(modeldrivername):
    """ Get the model driver directory """
    return os.path.join(KIM_MODEL_DRIVERS_DIR,modeldrivername)

def test_driver_dir(testdrivername):
    """ Get the test driver directory """
    return os.path.join(KIM_TEST_DRIVERS_DIR,testdrivername)

def test_driver_executable(testdrivername):
    """ Get the test driver executable """
    return os.path.join(test_driver_dir(testdrivername),testdrivername)

def reference_data_dir(referencedataname):
    """ Get the reference data directory """
    return os.path.join(KIM_REFERENCE_DATA_DIR,referencedataname)

def prediction_dir(predictionname):
    """ Get the prediction directory """
    return os.path.join(KIM_PREDICTIONS_DIR,predictionname)

def prediction_info(predictionname):
    """ Get the prediction file """
    return os.path.join(prediction_dir(predictionname), predictionname)

#==========================================
# Results in repo
#==========================================


def files_from_results(results):
    """ Given a dictionary of results, return the filenames for any files contained in the results """
    testname = results["_testname"]
    testdir = test_dir(testname)
    files = filter(None,(template.get_file(val,testdir) for key,val in results.iteritems()))
    return files
        

def write_result_to_file(results, pk=None):
    """ Given a dictionary of results, write it to the corresponding file, or create a new id
        
        This assumes the results already have the proper output Property IDs
        Write the property json file in its corresponding location
        and copy any files associated with it

        Also, update the property store for fast lookups
    
    """
    testname = results["_testname"]
    modelname = results["_modelname"]
    
    pr_id = kimid.new_kimid("PR")
    outputfolder = pr_id
    outputfilename = outputfolder

    with in_repo_dir(KIM_PREDICTIONS_DIR):
        os.mkdir(outputfolder)
        with open(os.path.join(outputfolder,outputfilename),"w") as fobj:
            simplejson.dump(results,fobj)

        #copy any corresponding files to the predictions directory
        files = files_from_results(results)
        if files:
            test_dir = test_dir(testname)
            for src in files:
                shutil.copy(os.path.join(test_dir,src),outputfolder)
    
    with prediction_store() as store:
        store[testname][modelname] = pr_id

    print "Wrote results in: {}".format(os.path.abspath(outputfilename))


def prediction_exists(testname,modelname):
    with prediction_store() as store:
        if testname in store:
            if modelname in store[testname]:
                return True
    return False

def load_info_file(filename):
    """ load a kim json pipeline info file """
    with open(filename) as fl:
        info = simplejson.load(fl)
    return info

def write_info_file_at(directory,info):
    """ write the dictionary to the corresponding directory """
    filepath = os.path.join(directory,PIPELINE_INFO_FILE)
    with open(filepath, "w") as fl:
        simplejson.dump(info,fl)

def persistent_info_file(filename,*args,**kwargs):
    return PersistentDict(filename,*args,format="json",**kwargs)

def test_info(testname,*args,**kwargs):
    """ load the info file for the corresponding test """
    location = os.path.join(test_dir(testname), PIPELINE_INFO_FILE)
    return persistent_info_file(location,*args,**kwargs)

def model_info(modelname, *args, **kwargs):
    """ load the info file for the corresponding model """
    location = os.path.join(model_dir(modelname), PIPELINE_INFO_FILE)
    return persistent_info_file(location,*args,**kwargs)

def prediction_store():
    """ return the prediction store """
    return PersistentDefaultDict(PREDICTION_STORE)

def prediction_info(pr):
    prpath = prediction_file(pr)
    return load_info_file(prpath)


#==========================================
# Processor helper files
#==========================================

def get_path(kid):
    """ Given a kimid give the path to the corresponding place """
    leader,pk,version = kimid.parse_kimid(kid)

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
    if leader=="PR":
        return prediction_dir(kid)


def data_from_rd(rd):
    """ Get the data for the rd id """


def data_from_pr_po(pr,po):
    """ Get data from a pr id and po id """
    info = prediction_info(pr)
    return info[po]


def data_from_te_mo_po(te,mo,po):
    """ Get data from a te, mo, po """
    with prediction_store() as store:
        pr = store[te][mo]
    return data_from_pr_po(pr,po)

#===========================================
# rsync utilities
#===========================================

def rsync_update():
    check_call("rsync -avz -e ssh {}@{}:{} {}".format(GLOBAL_USER,GLOBAL_HOST,GLOBAL_DIR,GLOBAL_DIR))

def test_model_to_priority(test, model):
    return 1
