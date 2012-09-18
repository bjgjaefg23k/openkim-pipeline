"""
Simple set of tools for having rsync commands go through
"""

from config import *
logger = logger.getChild("rsync_tools")
import os
import subprocess, tempfile
import database
from functools import partial

RSYNC_ADDRESS     = RSYNC_USER+"@"+RSYNC_HOST
RSYNC_REMOTE_ROOT = RSYNC_DIR
RSYNC_FLAGS = "-avuzRrhEc --progress --stats -e 'ssh -i /persistent/id_ecdsa_pipeline -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no' --exclude-from=/home/vagrant/openkim-pipeline/.rsync-exclude"
# --delete ensures that we delete files that aren't on remote

#RSYNC_PATH = '--rsync-path="cd {} && rsync"'.format(RSYNC_REMOTE_ROOT)
RSYNC_PATH = RSYNC_ADDRESS + ":" + RSYNC_REMOTE_ROOT

RSYNC_LOG_FILE_FLAG = "--log-file={}/rsync.log".format(LOG_DIR)

READ_APPROVED = os.path.join(RSYNC_PATH,"/read/approved/./")
READ_PENDING =  os.path.join(RSYNC_PATH,"/read/pending/./")
WRITE_APPROVED = os.path.join(RSYNC_PATH,"/write/approved/")
WRITE_PENDING = os.path.join(RSYNC_PATH,"/write/pending/")
WRITE_RESULTS = os.path.join(RSYNC_PATH, "/write/results/")

# RSYNC_TEST_MODE = True

if RSYNC_TEST_MODE:
    READ_APPROVED = READ_PENDING = WRITE_APPROVED = WRITE_PENDING = WRITE_RESULTS = os.path.join(RSYNC_PATH,"/write/testing/")

# TEMP_WRITE_PATH =   os.path.join(RSYNC_PATH,"")
# TEMP_READ_PATH =    os.path.join(RSYNC_PATH,"")
# REAL_WRITE_PATH =   os.path.join(RSYNC_PATH,"")
# REAL_READ_PATH =    os.path.join(RSYNC_PATH,"")

LOCAL_REPO_ROOT = KIM_REPOSITORY_DIR

#================================
# rsync wrappers
#================================

def rsync_command(files,read=True,path=None):
    """ run rsync, syncing the files (or folders) listed in files, assumed to be paths or partial
    paths from the LOCAL_REPO_ROOT
    """
    if path:
        full_path = RSYNC_PATH + path + "/./"
    else:
        full_path = RSYNC_PATH
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.file.write("\n".join(files))
        tmp.file.close()
        try:
            logger.info("running rsync for files: %r",files)
            if read:
                cmd = " ".join(["rsync",RSYNC_FLAGS,full_path,RSYNC_LOG_FILE_FLAG,"--files-from={}".format(tmp.name),LOCAL_REPO_ROOT])
            else:
                cmd = " ".join(["rsync",RSYNC_FLAGS,RSYNC_LOG_FILE_FLAG,"--files-from={}".format(tmp.name),LOCAL_REPO_ROOT,full_path])
            #print cmd
            #print open(tmp.name).read()
            logger.debug("rsync command = %r",cmd)
            subprocess.check_call(cmd, shell=True)
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

rsync_read = partial(rsync_command, read=True)

rsync_write = partial(rsync_command, read=False)

def j(*s):
    """ Convience for joining paths together """
    return os.path.join(*s)

RA = READ_APPROVED
RP = READ_PENDING
WA = WRITE_APPROVED
WP = WRITE_PENDING
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

#READS
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
    files = [j(WA,"te/"),j(WR,"tr/"),j(WA,ktf(modelname))]
    rsync_read(files)

def director_new_test_read(testname):
    """ when a director gets a new test """
    files = [j(WA,"mo/"),j(WR,"tr/"),j(WA,ktf(testname))]
    rsync_read(files)

def director_model_verification_read(modelname):
    """ when director needs to verify a model """
    files = [j(WA,"vm/"), j(WP,ktf(modelname))]
    rsync_read(files)

def director_test_verification_read(testname):
    """ when the director needs to verify a test """
    files = [j(WA,"vt/"), j(WP,ktf(testname)) ]
    rsync_read(files)

def director_build_read_approved(kim_name):
    """ when a director pulls before a make """
    files = [j(RA,ktf(kim_name))]
    rsync_read(files)

def director_build_read_pending(kim_name):
    """ when a director pulls before a make for a pending object """
    files = [j(RP,ktf(kim_name))]
    rsync_read(files)

# WRITES
def director_build_write_approved(kim_name):
    """ when a director does a make """
    rysnc_write([ktf(kim_name)],path=WA)

def director_build_write_pending(kim_name):
    """ when a director writes after a make for a pending object """
    rsync_write([ktf(kim_name)],path=WP)

#==================================
# worker methods
#==================================


def worker_verification_read(modelname,vmname):
    """ when a worker needs to run a model verification job """
    files = [j(WP,ktf(modelname)), j(WA,ktf(vmname))]
    rsync_read(files)

def worker_test_result_read(testname,modelname,depends):
    """ when a worker needs to run a test result """
    files = [j(WA,ktf(modelname)), j(WA,ktf(testname)), j(RA,"pr/")]
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
