# get us to our main code path
import os, sys, shutil
from subprocess import check_call

API = "/home/openkim/openkim-api"
CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
REPO2 = CODE_DIR + "/tests/repo"

def test_tunnels():
    import pipeline
    from config import *
    pipeline.open_ports(GLOBAL_PORT, PORT_RX, PORT_TX, GLOBAL_USER, GLOBAL_HOST, GLOBAL_IP)

def test_daemonconnect():
    import pipeline
    from config import *
    d = pipeline.Director()
    d.connect()
    d.disconnect()

def test_rxtx():
    import pipeline
    from config import *
    d = pipeline.Director()
    d.connect()
    d.disconnect()

