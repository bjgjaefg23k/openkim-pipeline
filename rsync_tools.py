"""
Simple set of tools for having rsync commands go through
"""

from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("rsync_tools")

import os
import subprocess, tempfile
import database
from functools import partial

# --delete ensures that we delete files that aren't on remote
RSYNC_FLAGS = "-vvrtLhptgo -uzREc --progress --stats -e 'ssh -i /persistent/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no' --exclude-from=/home/vagrant/openkim-pipeline/.rsync-exclude"
RSYNC_PATH = RSYNC_ADDRESS+":"+RSYNC_REMOTE_ROOT

RSYNC_LOG_FILE_FLAG = "--log-file={}/rsync.log".format(KIM_LOG_DIR)
RSYNC_LOG_PIPE_FLAG = " >> {} 2>&1".format(KIM_LOG_DIR+"/rsync_stdout.log")

READ_PENDING  = os.path.join(RSYNC_PATH,"/read/pending/./")
READ_APPROVED = os.path.join(RSYNC_PATH,"/read/approved/./")
WRITE_RESULTS = os.path.join(RSYNC_PATH, "/write/results/./")

#================================
# rsync wrappers
#================================
def rsync_command(files,read=True,path=None):
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
        try:
            logger.info("running rsync for files: %r",files)
            if read:    
                flags = "-f \"- */tr\" " + flags
                cmd = " ".join(["rsync", flags, full_path, RSYNC_LOG_FILE_FLAG,
                    "--files-from={}".format(tmp.name), RSYNC_LOCAL_ROOT, RSYNC_LOG_PIPE_FLAG])
            else:
                cmd = " ".join(["rsync", flags, RSYNC_LOG_FILE_FLAG,
                    "--files-from={}".format(tmp.name), RSYNC_LOCAL_ROOT, full_path, RSYNC_LOG_PIPE_FLAG])
            logger.debug("rsync command = %r",cmd)
            out = subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            logger.error("RSYNC FAILED!")
            raise

#======================================
# Helper methods
#======================================
def kid_to_folder(kid):
    """ Convert a kim_code to its directory """
    #obj = models.KIMObject(kid)
    #return obj.path
    name,leader,num,version = database.parse_kim_code(kid)
    path = os.path.join(leader.lower(),kid)
    return path

ktf = kid_to_folder

rsync_read  = partial(rsync_command, read=True)
rsync_write = partial(rsync_command, read=False)

def j(*s):
    """ Convience for joining paths together """
    return os.path.join(*s)

RA = READ_APPROVED
RP = READ_PENDING
# WA = WRITE_APPROVED
# WP = WRITE_PENDING
WR = WRITE_RESULTS

#=============================
# Not for realsy
#   This next section is just convience, not to be relied on
#============================
def full_test_sync():
    """ grab the whole repository """
    rsync_read([j(WP,"te/"),j(WP,"mo/"),j(WP,"md/"),j(WR,"tr/"),j(WP,"td/"),j(WP,"vt/"),j(WP,"vm/"),j(WR,"vr/"),j(WP,"pr/"),j(WP,"rd/")])


# def full_write():
#     """ write the whole repo """
#     rsync_write(["te/","mo/","md/","tr/","td/","vt/","vm/","vr/","pr/","rd/"])

# def temp_write(files,*args):
#     """ write things to the temporary write area """
#     rsync_command(files,read=False,path=TEMP_WRITE_PATH)

# def temp_read(files,*args):
#     """ pull things from the temporary read area """
#     rsync_command(files,read=True,path=TEMP_READ_PATH)


# def real_write(files,*args):
#     """ FORBIDDEN:
#         write things to the real write area """
#     rsync_command(files,read=False,path=REAL_WRITE_PATH)

# def real_read(files,*args):
#     """ read things from the real read directory """
#     rsync_command(files,read=True,path=REAL_READ_PATH)

#=================================
# director methods
#=================================
def director_full_approved_read():
    """ when a director trys to get everything """
    files = [j(RA,"te/"),j(RA,"mo/"),j(RA,"md/"),j(WR,"tr/"),j(RA,"td/"),j(RA,"vt/"),j(RA,"vm/"),j(WR,"vr/"),j(RA,"pr/"),j(RA,"rd/")]
    rsync_read(files)

def director_full_result_read():
    """ when a director gets all of the results """
    files = [j(WR,"tr/"), j(WR,"vr/")]
    rsync_read(files)

def director_new_model_read(modelname):
    """ when a director gets a new model """
    files = [j(RA,"te/"),j(RA,"td/"),j(WR,"tr/"),j(RA,"md/"),j(RA,ktf(modelname))]
    rsync_read(files)

def director_new_test_read(testname):
    """ when a director gets a new test """
    files = [j(RA,"mo/"),j(RA,"md/"),j(WR,"tr/"),j(RA,"td/"),j(RA,ktf(testname))]
    rsync_read(files)

def director_new_test_driver_read(testname):
    """ when a director gets a new test """
    files = [j(RA,"mo/"),j(RA,"md/"),j(WR,"tr/"),j(RA,"td/"),j(RA,"te/")]
    rsync_read(files)

def director_new_model_driver_read(testname):
    """ when a director gets a new test """
    files = [j(RA,"mo/"),j(RA,"md/"),j(WR,"tr/"),j(RA,"td/"),j(RA,"te/")]
    rsync_read(files)

def director_new_model_verification_read(vmname):
    """ when a director gets a new vm """
    files = [j(RA,"mo/"),j(RA,"md/"),j(RA,ktf(vmname))]
    rsync_read(files)

def director_new_test_verification_read(vtname):
    """ when a director gets a new vt """
    files = [j(RA,"te/"),j(RA,"td/"),j(RA,ktf(vtname))]
    rsync_read(files)

def director_model_verification_read(modelname):
    """ when director needs to verify a model """
    files = [j(RA,"vm/"), j(RA,"md/"), j(RP,ktf(modelname))]
    rsync_read(files)

def director_test_verification_read(testname):
    """ when the director needs to verify a test """
    files = [j(RA,"vt/"), j(RA,"td/"),j(RP,ktf(testname)) ]
    rsync_read(files)


#==================================
# worker methods
#==================================


def worker_verification_read(subject,verifier):
    """ when a worker needs to run a model verification job """
    files = [j(RP,ktf(subject)), j(RA,ktf(verifier))]
    rsync_read(files)

def worker_test_result_read(testname,modelname,depends):
    """ when a worker needs to run a test result """
    files = [j(RA,ktf(modelname)), j(RA,ktf(testname)), j(RA,"pr/")]
    # FIXME: Do we really need the PR directory???
    for depend in depends:
        if depend.startswith("TR"):
            files.append(j(WR,ktf(depend)))
        else:
            files.append(j(RA,ktf(depend)))
        # FIXME: Make sure that this will be in RA
    rsync_read(files)

def worker_verification_write(vrname):
    """ when a worker ran a model verification """
    rsync_write([ktf(vrname)],path=WR)

def worker_test_result_write(trname):
    """ when a worker ran a test result """
    rsync_write([ktf(trname)],path=WR)
