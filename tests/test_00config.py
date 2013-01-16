# get us to our main code path
import os, sys, shutil
from subprocess import check_call

API = "/home/vagrant/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"

def test_paths():
    assert os.environ['KIM_TESTS_DIR'] == REPO2+"/te/"
    assert os.environ['KIM_TEST_DRIVERS_DIR'] == REPO2+"/td/"
    assert os.environ['KIM_MODELS_DIR'] == REPO2+"/mo/"
    assert os.environ['KIM_MODEL_DRIVERS_DIR'] == REPO2+"/md/"
    
def test_hasfiles():
    assert os.path.exists(REPO2)
    assert os.path.exists(REPO2+"/mo")
    assert os.path.exists(REPO2+"/md")
    assert os.path.exists(REPO2+"/te")
    assert os.path.exists(REPO2+"/td")

def test_builds():
    os.chdir(API)
    check_call(". /tmp/env; makekim", shell=True)
    os.chdir(CODE_DIR)
    assert os.path.exists(API+"/KIM_API/libkim.so")

