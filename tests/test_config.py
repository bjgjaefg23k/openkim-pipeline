""" Some general test configuration settings """
""" Some basic testing imports """

# get us to our main code path
import os
import sys

CODE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
os.chdir(CODE_DIR)
sys.path.append(CODE_DIR)

from config import *

logger = logger.getChild("tests")
