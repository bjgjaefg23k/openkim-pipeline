"""
Simple set of tools for having rsync commands go through
"""

from config import *
logger = logger.getChild("rsync_tools")
import os
import subprocess, tempfile
import database

RSYNC_ADDRESS =     "sethnagroup@cerbo.ccmr.cornell.edu"
RSYNC_REMOTE_ROOT = "/home/sethnagroup/vagrant/openkim-repository"
RSYNC_FLAGS = "-avzR" # --delete ensures that we delete files that aren't on remote
#RSYNC_PATH = '--rsync-path="cd {} && rsync"'.format(RSYNC_REMOTE_ROOT)
RSYNC_PATH = RSYNC_ADDRESS + ":" + RSYNC_REMOTE_ROOT

RSYNC_LOG_FILE_FLAG = "--log-file={}/rsync.log".format(LOG_DIR)

TEMP_WRITE_PATH =   os.path.join(RSYNC_REMOTE_ROOT,"")
TEMP_READ_PATH =    os.path.join(RSYNC_REMOTE_ROOT,"")
REAL_WRITE_PATH =   os.path.join(RSYNC_REMOTE_ROOT,"")
REAL_READ_PATH =    os.path.join(RSYNC_REMOTE_ROOT,"")

LOCAL_REPO_ROOT = KIM_REPOSITORY_DIR


#================================
# rsync wrappers 
#================================

def rsync_command(files,read=True):
    """ run rsync, syncing the files (or folders) listed in files, assumed to be paths or partial
    paths from the LOCAL_REPO_ROOT
    """
    with tempfile.NamedTemporaryFile() as tmp:
        tmp.file.write("\n".join(files))
        tmp.file.close()
        try:
            logger.info("running rsync for files: %r",files)
            if read:
                cmd = " ".join(["rsync",RSYNC_FLAGS,RSYNC_PATH,RSYNC_LOG_FILE_FLAG,"--files-from={}".format(tmp.name),LOCAL_REPO_ROOT])
            else:
                cmd = " ".join(["rsync",RSYNC_FLAGS,RSYNC_LOG_FILE_FLAG,"--files-from={}".format(tmp.name),LOCAL_REPO_ROOT,RSYNC_PATH])
            #print cmd
            #print open(tmp.name).read()
            logger.debug("rsync command = %r",cmd)
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            logger.error("RSYNC FAILED!")
            raise

def rsync_read(files):
    """ Do an rsync pull of files """
    rsync_command(files,read=True)

def rsync_write(files):
    """ Do an rsync_write of files """
    rsync_command(files,read=False)


def full_sync():
    """ grab the whole repository """
    rsync_read(["te/","mo/","md/","tr/","td/","vc/","vr/","pr/","rd/"])

def full_write():
    """ write the whole repo """
    rsync_write(["te/","mo/","md/","tr/","td/","vc/","vr/","pr/","rd/"])


def temp_write(*args):
    """ write things to the temporary write area """

def temp_read(*args):
    """ pull things from the temporary read area """

def real_write(*args):
    """ FORBIDDEN:
        write things to the real write area """

def real_read(*args):
    """ read things from the real read directory """


def kid_to_folder(kid):
    """ Convert a kim_code to its directory """
    #obj = models.KIMObject(kid)
    #return obj.path
    name,leader,num,version = database.parse_kim_code(kid)
    path = os.path.join(leader.lower(),kid)
    return path

#=================================
# director methods
#=================================

def director_model_verification_read(modelname):
    """ when director needs to verify a model """
    files = ["vc/"]
    files.append(kid_to_folder(modelname))
    rsync_read(files)

def director_new_model_read(modelname):
    """ when a director gets a new model """
    files = ["te/","tr/"]
    files.append(kid_to_folder(modelname))
    rsync_read(files)

def director_new_test_read(testname):
    """ when a director gets a new test """
    files = ["mo/","tr/"]
    files.append(kid_to_folder(testname))
    rsync_read(files)

#==================================
# worker methods
#==================================


def worker_model_verification_read(modelname,vcname,depends):
    """ when a worker needs to run a verification job """
    files = [kid_to_folder(modelname), kid_to_folder(vcname)]
    for depend in depends:
        files.append(kid_to_folder(depend))
    rsync_read(files)

def worker_test_result_read(testname,modelname,depends):
    """ when a worker needs to run a test result """
    files = [kid_to_folder(modelname),kid_to_folder(testname)]
    for depend in depends:
        files.append(kid_to_folder(depend))
    rsync_read(files)

def worker_model_verification_write(vrname):
    """ when a worker ran a model verification """
    files = [kid_to_folder(vrname)]
    rsync_write(files)

def worker_test_result_write(trname):
    """ when a worker ran a test result """
    files = [kid_to_folder(trname)]
    rsync_write(files)
