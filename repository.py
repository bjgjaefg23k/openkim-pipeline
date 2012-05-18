""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess
from contextlib import contextmanager
import kimservice

#==============================
# KIM FLAGS
#===============================

#get the kim directories
KIM_DIR = os.environ["KIM_DIR"]
KIM_API_DIR = os.environ.get("KIM_API_DIR",
        os.path.join(KIM_DIR,"KIM_API"))
KIM_MODELS_DIR = os.environ.get("KIM_MODELS_DIR",
        os.path.join(KIM_DIR,"MODELs"))
KIM_MODEL_DRIVERS_DIR = os.environ.get("KIM_MODEL_DRIVERS_DIR",
        os.path.join(KIM_DIR,"MODEL_DRIVERs"))
KIM_TESTS_DIR = os.environ.get("KIM_TESTS_DIR",
        os.path.join(KIM_DIR,"TESTs"))

#get all of the models
KIM_MODELS = [ dir for dir in os.listdir(KIM_MODELS_DIR) if os.path.isdir(os.path.join(KIM_MODELS_DIR,dir)) ]
#and all of the tests
KIM_TESTS =  [ dir for dir in os.listdir(KIM_TESTS_DIR) if os.path.isdir(os.path.join(KIM_TESTS_DIR,dir)) ]

#get the repository dir from the symlink
KIM_REPOSITORY_DIR = os.readlink('openkim-repository')

#============================
# Silly git stuff
#============================

@contextmanager
def in_repo_dir():
    """Change to repo directory to execute code, then change back"""
    cwd = os.getcwd()
    os.chdir(KIM_REPOSITORY_DIR)
    yield
    os.chdir(cwd)

def pull(remote='origin',branch='master'):
    """ do a git pull """
    with in_repo_dir():
        return subprocess.call(['git','pull',remote,branch])

def push(remote='origin',branch='master'):
    """ do a git push """
    with in_repo_dir():
        return subprocess.call(['git','push',remote,branch])

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
    return (test for test in KIM_TESTS if valid_match(test,modelname) )

def models_for_test(testname):
    return (model for model in KIM_MODELS if valid_match(testname,model) )

def test_executable(testname):
    """ get the executable for a test """
    return os.path.join(KIM_TESTS_DIR,testname,testname)
