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

#get the kim directories
KIM_DIR = os.environ["KIM_DIR"] #the bash shell environ
KIM_API_DIR = os.environ.get("KIM_API_DIR",
        os.path.join(KIM_DIR,"KIM_API"))

#get the repository dir from the symlink
KIM_REPOSITORY_DIR = os.environ["KIM_REPOSITORY_DIR"]
KIM_PIPELINE_DIR = os.path.abspath(os.path.dirname(__file__))

METADATA_INFO_FILE = "metadata.json"
PIPELINE_INFO_FILE = "pipelineinfo.json"
INPUT_FILE = "pipeline.in"
OUTPUT_FILE = "pipeline.out"    #with their words : property ids
STDOUT_FILE = "pipeline.stdout"
TEMP_INPUT_FILE = "pipeline.in.tmp"
KIMLOG_FILE = "kim.log"

#===========================
# Directory codes
#===========================

KIM_TEST_RESULTS_DIR = os.path.abspath(os.path.join(KIM_REPOSITORY_DIR,"tr"))
KIM_REFERENCE_DATA_DIR = os.path.abspath(os.path.join(KIM_REPOSITORY_DIR,"rd"))
KIM_MODELS_DIR = os.path.abspath(os.path.join(KIM_REPOSITORY_DIR,"mo"))
KIM_MODEL_DRIVERS_DIR = os.path.abspath(os.path.join(KIM_REPOSITORY_DIR,"md"))
KIM_TESTS_DIR = os.path.abspath(os.path.join(KIM_REPOSITORY_DIR,"te"))
KIM_TEST_DRIVERS_DIR = os.path.abspath(os.path.join(KIM_REPOSITORY_DIR,"td"))
KIM_REPO_DIRS = [KIM_TEST_RESULTS_DIR,KIM_REFERENCE_DATA_DIR,
        KIM_MODELS_DIR,KIM_MODEL_DRIVERS_DIR,KIM_TESTS_DIR,KIM_TEST_DRIVERS_DIR]


#get all of the models
KIM_MODELS = [ dir for dir in os.listdir(KIM_MODELS_DIR) if os.path.isdir(os.path.join(KIM_MODELS_DIR,dir)) ]
#and all of the tests
KIM_TESTS =  [ dir for dir in os.listdir(KIM_TESTS_DIR) if os.path.isdir(os.path.join(KIM_TESTS_DIR,dir)) ]
KIM_TEST_DRIVERS = [ dir for dir in os.listdir(KIM_TEST_DRIVERS_DIR) if os.path.isdir(os.path.join(KIM_TEST_DRIVERS_DIR,dir))]
KIM_MODEL_DRIVERS = [ dir for dir in os.listdir(KIM_MODEL_DRIVERS_DIR) if os.path.isdir(os.path.join(KIM_MODEL_DRIVERS_DIR,dir))]


#============================
# Settings for remote access
#============================

GLOBAL_IP   = "127.0.0.1"
GLOBAL_PORT = 14177

GLOBAL_USER = "pipeline"
GLOBAL_HOST = "pipeline.openkim.org"
GLOBAL_DIR  = "/write/pending/"

RSYNC_USER  = "pipeline"
RSYNC_HOST  = "openkim.org"
RSYNC_DIR   = "/write/pending/"

#============================
# Runner Internals
#============================

RUNNER_TIMEOUT = 300

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

#create a console logger
console_handler = logging.StreamHandler()
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
