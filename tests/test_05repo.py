import os, sys, shutil
from subprocess import check_call

API = "/home/openkim/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"


def test_orm_testobj():
    import kimobjects 
    test = kimobjects.Test("LatticeConstantCubicEnergy_Al_fcc__TE_000000000000_000")    
    assert len( list(test.models) ) == 1
    assert test.kim_code == "LatticeConstantCubicEnergy_Al_fcc__TE_000000000000_000"
    assert test.kim_code_name == "LatticeConstantCubicEnergy_Al_fcc"
    assert test.kim_code_leader == "TE"
    assert test.kim_code_version == "000"

def test_testobj2():
    import kimobjects 
    test = kimobjects.Test("LatticeConstantCubicEnergy_Al_fcc__TE_000000000000_000")    
    test.infile.readlines()
    
def test_orm_testobj_driver():
    import kimobjects 
    test = kimobjects.Test("LatticeConstantCubicEnergy_Ar_fcc__TE_000000000001_000")
    assert "LatticeConstantCubicEnergy__TD_000000000000_000"  == next(test.test_drivers).kim_code



