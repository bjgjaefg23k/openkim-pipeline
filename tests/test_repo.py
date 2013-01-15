import os
import sys
import shutil

API = "/home/vagrant/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"
os.chdir(CODE_DIR)
sys.path.append(CODE_DIR)


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
    os.system("/usr/bin/env `cat /tmp/env` make clean && make >> /dev/null 2>&1")
    os.chdir(CODE_DIR)
    assert os.path.exists(API+"/KIM_API/libkim.so")

def test_orm_testobj():
    import models
    test = models.Test("LatticeConstantCubicEnergy_Al_fcc__TE_000000000000_000")    
    assert len( list(test.models) ) == 1
    assert test.kim_code == "LatticeConstantCubicEnergy_Al_fcc__TE_000000000000_000"
    assert test.kim_code_name == "LatticeConstantCubicEnergy_Al_fcc"
    assert test.kim_code_leader == "TE"
    assert test.kim_code_version == "000"

   
def test_orm_testobj_driver():
    import models
    test = models.Test("LatticeConstantCubicEnergy_Ar_fcc__TE_000000000001_000")
    assert "LatticeConstantCubicEnergy__TD_000000000000_000"  == list(test.test_drivers)[0].kim_code

def test_rsync_write():
    pass

def test_rsync_read():
    pass

def test_cleanup():
    os.chdir(API)
    os.system("/usr/bin/env `cat /tmp/env` make clean >> /dev/null 2>&1")
    assert not os.path.exists(API+"/KIM_API/libkim.so")
