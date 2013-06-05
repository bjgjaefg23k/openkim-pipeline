"""
config.py holds all of the constants that are used throughout the pipeline scripts.

Mostly folders and a preliminary list of all of the available tests and models, as well
as the exceptions that will be used throughtout.

By convention the constants are all in UPPER_CASE_WITH_UNDERSCORES,
and this module is imported in star from at the top of all of the scripts::

    from config import *
"""
import os

# Setting up global truths - provide these with environment variables!
PIPELINE_REMOTE    = False  # are we even connected remotely
PIPELINE_GATEWAY   = False  # are we running as the gateway
PIPELINE_DEBUG     = False  # which pipeline to use - production or debug
PIPELINE_DEBUG_VBS = False  # do we want all information to print

if os.environ.has_key("PIPELINE_REMOTE"):
    PIPELINE_REMOTE = True

if os.environ.has_key("PIPELINE_DEBUG"):
    PIPELINE_DEBUG = True

if os.environ.has_key("PIPELINE_GATEWAY"):
    PIPELINE_GATEWAY = True

#===============================
# KIM FLAGS
#===============================
KIM_REPOSITORY_DIR = "/home/vagrant/openkim-repository"
KIM_PIPELINE_DIR   = os.path.abspath(os.path.dirname(__file__))
KIM_LOG_DIR        = os.path.join(KIM_PIPELINE_DIR, "logs")

INPUT_FILE      = "pipeline.in"
TEMP_INPUT_FILE = "pipeline.in.tmp"
TEMPLATE_FILE   = 'pipeline.yaml'
TEMPLATE_OUT    = "pipeline.yaml.processed"
TR_OUTPUT       = "pipeline.tr.processed"
STDOUT_FILE     = "pipeline.stdout"
STDERR_FILE     = "pipeline.stderr"
KIMLOG_FILE     = "kim.log"

#==============================
# Settings for remote access
#==============================
GLOBAL_IP   = "127.0.0.1"
GLOBAL_TOUT = 1
GLOBAL_USER = "pipeline"
GLOBAL_HOST = "pipeline.openkim.org"
GLOBAL_KEY  = "/persistent/id_rsa"

WEBSITE_ROOT    = "/"
if PIPELINE_DEBUG:
    GATEWAY_ROOT = "/repository_dbg/"
else:
    GATEWAY_ROOT = "/repository/"

RSYNC_USER  = "pipeline"
RSYNC_HOST  = "pipeline.openkim.org"
RSYNC_ADDRESS     = RSYNC_USER+"@"+RSYNC_HOST
RSYNC_LOCAL_ROOT  = KIM_REPOSITORY_DIR
RSYNC_REMOTE_ROOT = GATEWAY_ROOT
RSYNC_EXCLUDE_FILE= KIM_PIPELINE_DIR+"/.rsync-exclude"

if PIPELINE_DEBUG:
    BEAN_PORT = 14174
    PORT_TX   = 14173
    PORT_RX   = 14172
else:
    BEAN_PORT = 14177
    PORT_TX   = 14176
    PORT_RX   = 14175

if PIPELINE_GATEWAY:
    PORT_TX, PORT_RX = PORT_RX, PORT_TX  # swap RX, TX
    RSYNC_LOCAL_ROOT  = GATEWAY_ROOT
    RSYNC_REMOTE_ROOT = WEBSITE_ROOT
    GLOBAL_KEY = "/home/ubuntu/id_ecdsa_pipeline"

TUBE_WEB_UPDATES = "web_updates"
TUBE_WEB_RESULTS = "web_results"
TUBE_UPDATES     = "updates"
TUBE_RESULTS     = "results"
TUBE_JOBS        = "jobs"
TUBE_ERRORS      = "errors"
TUBE_LOGS        = "logs"

PIPELINE_WAIT    = 1
PIPELINE_TIMEOUT = 60
PIPELINE_MSGSIZE = 2**16
PIPELINE_JOB_TIMEOUT = 3600*24 

#============================
# Runner Internals
#============================
RUNNER_TIMEOUT = 60*60*24*5 # sec-min-hr-days

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

class PipelineQueryError(Exception):
    """ there was an error while attempting a remote query """
