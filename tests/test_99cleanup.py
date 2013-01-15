import os, sys, shutil
from subprocess import check_call

API = "/home/vagrant/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"


def test_cleanup():
    os.chdir(API)
    os.system("(. /tmp/env; make clean >> /dev/null 2>&1)")
    assert not os.path.exists(API+"/KIM_API/libkim.so")
