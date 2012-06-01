""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess, simplejson
from contextlib import contextmanager
import kimservice, kimid
from persistentdict import PersistentDict
from config import *
from subprocess import check_call

#============================
# Silly git stuff
#============================

@contextmanager
def in_repo_dir(subdir=None):
    """Change to repo directory to execute code, then change back"""
    cwd = os.getcwd()
    os.chdir(os.path.join(KIM_REPOSITORY_DIR,subdir or ""))
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

#==========================================
# Results in repo
#==========================================

PREDICTION_FORM = "{}-{}"

def write_result_to_file(results, pk=None):
    """ Given a dictionary of results, write it to the corresponding file, or create a new id """
    testname = results["_testname"]
    modelname = results["_modelname"]
    
    outputfilename = PREDICTION_FORM.format(testname,modelname)

    with in_repo_dir("PREDICTIONs"):
        with open(outputfilename,"w") as fobj:
            simplejson.dump(results,fobj)
    
    print "Wrote results in: {}".format(os.path.abspath(outputfilename))


def prediction_exists(testname,modelname):
    outputfilename = PREDICTION_FORM.format(testname,modelname)
    with in_repo_dir("PREDICTIONs"):
        if os.path.exists(outputfilename):
            return True
    return False

def load_info_file(filename):
    """ loat a kim json pipeline info file """
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

def test_kimid(testname):
    #See if id exists
    try:
        return test_info(testname)["kimid"]
    except KeyError:
        #generate a new kimid
        newid = kimid.new_kimid("TE")
        infodict = test_info(testname)
        infodict["kimid"] = newid
        infodict.sync()
        return newid

def model_kimid(modelname):
    return model_info(modelname)["kimid"]

#===========================================
# rsync utilities
#===========================================

def rsync_update():
    check_call("rsync -avz -e ssh {}@{}:{} {}".format(GLOBAL_USER,GLOBAL_HOST,GLOBAL_DIR,GLOBAL_DIR))

def test_model_to_priority(test, model):
    return 1
