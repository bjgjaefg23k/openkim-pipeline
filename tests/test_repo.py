import os
import sys
import shutil

API = "/home/vagrant/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"
os.chdir(CODE_DIR)
sys.path.append(CODE_DIR)

from config import *
import models

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
    os.system("/usr/bin/env `cat /tmp/env` make >> /dev/null 2>&1")
    os.chdir(CODE_DIR)
    assert os.path.exists(API+"/KIM_API/libkim.so")

def test_orm_testobj():
    test = models.Test("LatticeConstantCubicEnergy_Fe_fcc__TE_248695510051_000")    
    assert len( list(test.models) ) == 3
    assert test.kim_code == "LatticeConstantCubicEnergy_Fe_fcc__TE_248695510051_000"
    assert test.kim_code_name == "LatticeConstantCubicEnergy_Fe_fcc"
    assert test.kim_code_leader == "TE"
    assert test.kim_code_version == "000"

   
def test_orm_testobj_driver():
    test = models.Test("LatticeConstantCubicEnergy_Fe_fcc__TE_248695510051_000")
    assert "LatticeConstantCubicEnergy__TD_373755852346_000"  == list(test.test_drivers)[0].kim_code

def test_rsync_write():
    pass

def test_rsync_read():
    pass

