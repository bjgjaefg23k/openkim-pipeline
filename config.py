"""
config.py holds all of the constants that are used throughout the pipeline scripts.

Mostly folders and a preliminary list of all of the available tests and models, as well
as the exceptions that will be used throughtout.

By convention the constants are all in UPPER_CASE_WITH_UNDERSCORES,
and this module is imported in star from at the top of all of the scripts::

    from config import *

doing so, we'll have access to all of the constants as well as the logger which ought to be
made a child of eary::

    logger = logger.getChild("<child name>")

"""

import os

#==============================
# KIM FLAGS
#===============================
if os.environ.has_key("PIPELINE_DEBUG"):
    PIPELINE_DEBUG = True
    print "DEBUG MODE: ON"
else:
    PIPELINE_DEBUG = False

#get the repository dir from the symlink
KIM_REPOSITORY_DIR = os.environ["KIM_REPOSITORY_DIR"]
KIM_PIPELINE_DIR = os.path.abspath(os.path.dirname(__file__))

METADATA_INFO_FILE = "metadata.json"
PIPELINE_INFO_FILE = "pipelineinfo.json"
INPUT_FILE = "pipeline.in"
OUTPUT_FILE = "pipeline.out"    #with their words : property ids
STDOUT_FILE = "pipeline.stdout"
STDERR_FILE = "pipeline.stderr"
TEMP_INPUT_FILE = "pipeline.in.tmp"
KIMLOG_FILE = "kim.log"

#============================
# Settings for remote access
#============================
if PIPELINE_DEBUG == True:
    GLOBAL_PORT = 14176
else:
    GLOBAL_PORT = 14177
    
GLOBAL_IP   = "127.0.0.1"
GLOBAL_USER = "pipeline"
GLOBAL_HOST = "pipeline.openkim.org"

RSYNC_USER  = "pipeline"
RSYNC_HOST  = "pipeline.openkim.org"
RSYNC_DIR   = "/repository/"
RSYNC_TEST_MODE = False

#============================
# Runner Internals
#============================
RUNNER_TIMEOUT = 60*60*24*5 # sec-min-hr-days

#=============================
# Logging stuff
#=============================
import logging, logging.handlers

logger = logging.getLogger("pipeline")
logger.setLevel(logging.DEBUG)

#formatter
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

LOG_DIR = os.path.join(KIM_PIPELINE_DIR,"logs")

#create a rotating file handler
rotfile_handler = logging.handlers.RotatingFileHandler(os.path.join(LOG_DIR,
        "pipeline.log"),mode='a',
        backupCount=5,maxBytes=10*1024*1024)
rotfile_handler.setLevel(logging.DEBUG)
rotfile_handler.setFormatter(log_formatter)
logger.addHandler(rotfile_handler)

import pygmentlog
class PygmentHandler(logging.StreamHandler):
    """ A beanstalk logging handler """
    def __init__(self):
        super(PygmentHandler,self).__init__()

    def emit(self,record):
        """ Send the message """
        err_message = self.format(record)
        pygmentlog.pygmentize(err_message)

#create a console logger
console_handler = PygmentHandler()
console_handler.setLevel(logging.INFO)
console_handler.setFormatter(log_formatter)
logger.addHandler(console_handler)

#====================================
# KIM ERRORS
#====================================
class InvalidKIMID(Exception):
    """ Used for invalid KIM IDS """

class PipelineResultsError(Exception):
    """ Used when the results are not of an understood type, i.e. not a valid JSON string """

class KIMRuntimeError(Exception):
    """ General purpose KIM Api Error, used if an invocation of the KIM_API doesn't behave """

class PipelineFileMissing(Exception):
    """ If a file we rely on is missing """

class PipelineTimeout(Exception):
    """ If a test time outs """

class PipelineDataMissing(Exception):
    """ If requested data doesn't exist """

class PipelineSearchError(Exception):
    """ If a search turns up bad, e.g. someone asks for a kim_code that we can't match against"""

class PipelineTemplateError(Exception):
    """ some kind of templating format is wrong, doesn't conform to our templating directives """
