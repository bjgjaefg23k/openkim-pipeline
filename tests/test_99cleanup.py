import os, sys, shutil, glob
from subprocess import check_call

API = "/home/openkim/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"

def test_cleanup():
    os.chdir(API)
    os.system("(. /tmp/env; make clean >> /dev/null 2>&1)")
    assert not os.path.exists(API+"/KIM_API/libkim.so")

def test_objectsexist():
    assert len(glob.glob(REPO2+"/mo/*/*.o")) == 0
    assert len(glob.glob(REPO2+"/mo/*/*.so")) == 0
    assert len(glob.glob(REPO2+"/mo/*/*.a")) == 0

def test_kimstr():
    assert len(glob.glob(REPO2+"/mo/*/*kim_str.o")) == 0

