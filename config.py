"""
config.py holds all of the constants that are used throughout the pipeline scripts.

Mostly folders and a preliminary list of all of the available tests and models, as well
as the exceptions that will be used throughtout.

By convention the constants are all in UPPER_CASE_WITH_UNDERSCORES,
and this module is imported in star from at the top of all of the scripts::

    from config import *
"""
import os
import re

#======================================
# the environment parser
#======================================
def read_environment(filename):
    conf = {}
    lines = open(filename).readlines()
    for line in lines:
        if not re.match(r"^[A-Za-z0-9\_]+\=.", line):
            continue
        var, val = line.strip().split("=")
        search = re.search(r"(\$[A-Za-z0-9\_]+)", val) 
        if search:
            for rpl in search.groups():
                val = val.replace(rpl, conf[rpl[1:]])
        conf[var] = val
    return conf

ENVIRONMENT_FILE = "/pipeline/environment"
CONF = read_environment(ENVIRONMENT_FILE)
CONF.update(read_environment(CONF["FILE_CONF_EXTRA"]))

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
HOME               = os.path.expanduser('~')
KIM_REPOSITORY_DIR = os.path.join(HOME,"openkim-repository")
KIM_PIPELINE_DIR   = os.path.abspath(os.path.dirname(__file__))
KIM_LOG_DIR        = os.path.join(KIM_PIPELINE_DIR, "logs")
KIM_API_DIR        = os.path.join(HOME,"openkim-api")
KIM_API_LIB_DIR    = os.path.join(KIM_API_DIR,"KIM_API")
KIM_API_CHECK_MATCH_UTIL = os.path.join(KIM_API_LIB_DIR,"openkim-api-descriptor-file-match")

OUTPUT_DIR      = "output"
INPUT_FILE      = "pipeline.stdin"
TEMPLATE_FILE   = "pipeline.yaml"
CONFIG_FILE     = "kimspec.ini"
TEMP_INPUT_FILE = os.path.join(OUTPUT_DIR,"pipeline.processed.stdin")
STDOUT_FILE     = os.path.join(OUTPUT_DIR,"pipeline.stdout")
STDERR_FILE     = os.path.join(OUTPUT_DIR,"pipeline.stderr")
KIMLOG_FILE     = os.path.join(OUTPUT_DIR,"kim.log")
RESULT_FILE     = os.path.join(OUTPUT_DIR,"results.yaml")

#==============================
# Settings for remote access
#==============================
GLOBAL_IP   = "127.0.0.1"
GLOBAL_TOUT = 1
GLOBAL_USER = "pipeline"
GLOBAL_HOST = "pipeline.openkim.org"
GLOBAL_KEY  = CONF["FILE_IDRSA"]

WEBSITE_ROOT    = "/"
if PIPELINE_DEBUG:
    GATEWAY_ROOT = "/storage/repository_dbg/"
else:
    GATEWAY_ROOT = "/storage/repository/"

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
    MONGODB   = "database_dbg"
    GATEWAY_PORT_JOBS = 1111
    GATEWAY_PORT_LOGS = 1112
else:
    BEAN_PORT = 14177
    PORT_TX   = 14176
    PORT_RX   = 14175
    MONGODB   = "database"
    GATEWAY_PORT_JOBS = 1113
    GATEWAY_PORT_LOGS = 1114

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

class PipelineRuntimeError(Exception):
    """ we had any number of errors while running """
    def __init__(self, e, extra=""):
        self._e = e
        self.extra = extra

    def __getattr__(self, name):
        return getattr(self._e, name)

    def __str__(self):
        if isinstance(self._e, PipelineRuntimeError):
            return str(self._e)
        else:
            return '%s: %s\n\n%s' % (self._e.__class__.__name__, str(self._e), self.extra)



