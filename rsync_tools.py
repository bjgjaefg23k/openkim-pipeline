"""
Simple set of tools for having rsync commands go through
"""

import config as cf
from logger import logging
logger = logging.getLogger("pipeline").getChild("rsync_tools")

import os
import subprocess
import tempfile
from database import parse_kim_code
from functools import partial

# --delete ensures that we delete files that aren't on remote
RSYNC_FLAGS  = "-vvrLhzREc --progress --stats -e "
RSYNC_FLAGS += "'ssh -i "+cf.GLOBAL_KEY+" -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no'"
RSYNC_FLAGS += " --exclude-from="+cf.RSYNC_EXCLUDE_FILE

RSYNC_ADDRESS = cf.RSYNC_USER+"@"+cf.RSYNC_HOST
RSYNC_PATH = RSYNC_ADDRESS+":"+cf.RSYNC_REMOTE_ROOT
RSYNC_LOG_FILE_FLAG = "--log-file={}/rsync.log".format(cf.KIM_LOG_DIR)
RSYNC_LOG_PIPE_FLAG = " >> {} 2>&1".format(cf.KIM_LOG_DIR+"/rsync_stdout.log")

if cf.PIPELINE_GATEWAY:
    READ_PENDING  = os.path.join(RSYNC_PATH, "/curators-to-pipeline-interface/pending/./")
    READ_APPROVED = os.path.join(RSYNC_PATH, "/curators-to-pipeline-interface/approved/./")
    if cf.PIPELINE_DEBUG:
        WRITE_RESULTS = os.path.join(RSYNC_PATH, "/pipeline/test-result-uploads-dbg/incoming/./")
    else:
        WRITE_RESULTS = os.path.join(RSYNC_PATH, "/pipeline/test-result-uploads/incoming/./")
else:
    READ_PENDING  = os.path.join(RSYNC_PATH, "/./")
    READ_APPROVED = os.path.join(RSYNC_PATH, "/./")
    WRITE_RESULTS = os.path.join(RSYNC_PATH, "/./")

#================================
# rsync wrappers
#================================
def rsync_command(files, read=True, path=None, delete=False):
    """ run rsync, syncing the files (or folders) listed in files, assumed to be paths or partial
    paths from the RSYNC_LOCAL_ROOT
    """
    if path:
        full_path = RSYNC_PATH + path + "/./"
    else:
        full_path = RSYNC_PATH
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.file.write("\n".join(files))
        tmp.file.close()
        flags = RSYNC_FLAGS

        if delete:
            flags = "--delete "+flags

        try:
            logger.info("running rsync for files: %r",files)
            if read:    
                cmd = " ".join(["rsync", flags, full_path, RSYNC_LOG_FILE_FLAG,
                    "--files-from={}".format(tmp.name), cf.RSYNC_LOCAL_ROOT, RSYNC_LOG_PIPE_FLAG])
            else:
                cmd = " ".join(["rsync", flags, RSYNC_LOG_FILE_FLAG,
                    "--files-from={}".format(tmp.name), cf.RSYNC_LOCAL_ROOT, full_path, RSYNC_LOG_PIPE_FLAG])
            logger.debug("rsync command = %r",cmd)
            out = subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            logger.exception("RSYNC FAILED!")
            cf.RsyncRuntimeError("Rsync command failed `%s`" % cmd)

def rsync_command_read_wildcard(files,path=None):
    """ run rsync, syncing the files (or folders) listed in files, assumed to be paths or partial
    paths from the RSYNC_LOCAL_ROOT
    """
    for filename in files:
        if path:
            full_path = RSYNC_PATH + path + "/./"
        else:
            full_path = RSYNC_PATH
        full_path += filename

        flags = RSYNC_FLAGS
        try:
            logger.info("running rsync for files: %r",filename)
            cmd = " ".join(["rsync", flags, full_path, RSYNC_LOG_FILE_FLAG,
                            cf.RSYNC_LOCAL_ROOT, RSYNC_LOG_PIPE_FLAG])
            logger.debug("rsync command = %r",cmd)
            out = subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError as e:
            logger.exception("RSYNC FAILED!")
            cf.RsyncRuntimeError("Rsync command failed `%s`" % cmd)

#======================================
# Helper methods
#======================================
def kid_to_folder(kid):
    """ Convert a kim_code to its directory """
    name,leader,num,version = parse_kim_code(kid)
    path = os.path.join(leader.lower(),kid)
    return path

def kid_to_folder_wild(kid):
    """ Convert a kim_code to its directory """
    name,leader,num,version = parse_kim_code(kid)
    path = os.path.join(leader.lower(),"*"+kid+"*")
    return path

ktf = kid_to_folder
ktfw = kid_to_folder_wild

rsync_read  = partial(rsync_command, read=True)
rsync_write = partial(rsync_command, read=False)
rsync_read_wild = partial(rsync_command_read_wildcard)

def j(*s):
    """ Convience for joining paths together """
    return os.path.join(*s)

RA = READ_APPROVED
RP = READ_PENDING
WR = WRITE_RESULTS

def gateway_read(kimcode, approved=True):
    # first, read everything from the /read directory, except all mentions of tr/
    if approved:
        rsync_read_wild([j(RA,ktfw(kimcode))])
    else:
        rsync_read_wild([j(RP,ktfw(kimcode))])

def gateway_write_result(leader, kimcode):
    # write the results back to the webserver in the appropriate place
    rsync_write([j(leader,kimcode)], path=WR)

def gateway_full_read():
    """ when a director trys to get everything """
    files = [j(RA,"te/"),j(RA,"mo/"),j(RA,"md/"),j(RA,"td/"),j(RA,"tv/"),j(RA,"mv/"),j(RA,"rd/")]
    rsync_read(files, delete=True)

#=================================
# director methods
#=================================
def director_approved_read():
    """ when a director trys to get everything """
    files = [j(RA,"te/"),j(RA,"mo/"),j(RA,"md/"),j(RA,"td/"),j(RA,"tv/"),j(RA,"mv/")]
    rsync_read(files, delete=True)

def director_pending_read(kimobj):
    """ when the director needs to verify a test """
    files = [j(RP,ktf(testname))]
    rsync_read(files)

def director_new_model_read(modelname):
    """ when a director gets a new model """
    files = [j(RA,"te/"),j(RA,"td/"),j(RA,"md/"),j(RA,ktf(modelname))]
    rsync_read(files)

def director_new_test_read(testname):
    """ when a director gets a new test """
    files = [j(RA,"mo/"),j(RA,"md/"),j(RA,"td/"),j(RA,ktf(testname))]
    rsync_read(files)

def director_new_test_driver_read(testname):
    """ when a director gets a new test """
    files = [j(RA,"mo/"),j(RA,"md/"),j(RA,"td/"),j(RA,"te/")]
    rsync_read(files)

def director_new_model_driver_read(testname):
    """ when a director gets a new test """
    files = [j(RA,"mo/"),j(RA,"md/"),j(RA,"td/"),j(RA,"te/")]
    rsync_read(files)

def director_new_model_verification_read(vmname):
    """ when a director gets a new vm """
    files = [j(RA,"mo/"),j(RA,"md/"),j(RA,ktf(vmname))]
    rsync_read(files)

def director_new_test_verification_read(vtname):
    """ when a director gets a new vt """
    files = [j(RA,"te/"),j(RA,"td/"),j(RA,ktf(vtname))]
    rsync_read(files)


#==================================
# worker methods
#==================================
def worker_read(runner, subject, depends, pending=False):
    """ when a worker needs to run a model verification job """
    subj_fldr = RP if pending else RA
    files = [j(RA,ktf(runner)), j(subj_fldr,ktf(subject))]
    for depend in depends:
        files.append(j(RA,ktf(depend)))
    rsync_read(files)

def worker_write(rpath):
    """ when a worker ran a model verification """
    rsync_write([rpath],path=WR)

