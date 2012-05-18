""" This should contain some nice functions and methods for dealing
with the repository structure """

import sys, os, subprocess
from contextlib import contextmanager
import kimservice

#get the kim dir
KIM_DIR = os.environ["KIM_DIR"]

#try to get the relevant directories
try:
    KIM_MODEL_DIR = os.environ["KIM_MODEL_DIR"]
except KeyError:
    KIM_MODEL_DIR = os.path.join(KIM_DIR,"MODELs")

#try to get the tests directory
try:
    KIM_TEST_DIR = os.environ["KIM_TEST_DIR"]
except KeyError:
    KIM_TEST_DIR = os.path.join(KIM_DIR,"TESTs")

#get all of the models
KIM_MODELS = [ dir for dir in os.listdir(KIM_MODEL_DIR) if os.path.isdir(os.path.join(KIM_MODEL_DIR,dir)) ]
#and all of the tests
KIM_TESTS =  [ dir for dir in os.listdir(KIM_TEST_DIR) if os.path.isdir(os.path.join(KIM_TEST_DIR,dir)) ]

#get the repository dir from the symlink
KIM_REPOSITORY_DIR = os.readlink('openkim-repository')

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

#######################################
# Some kim api wrapped things
#######################################

def valid_match(testname,modelname):
    """ Test to see if a test and model match using the kim API, returns bool """
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
