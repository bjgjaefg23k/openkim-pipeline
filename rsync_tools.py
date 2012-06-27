"""
Simple set of tools for having rsync commands go through

Times we read and write


READS
    Director:
        upon new model, must get model directory
            and then be able to generate matches and know whether results exist
            results existing can be database call
            and the entire tests directory

            MO dir                          from REAL_READ
            whole tests dir                 from REAL_READ
            way to check TRs                from DATABASE?

        upon a new test
            whole models dir                from REAL_READ
            test dir                        from REAL_READ
            way to check test results       from DATABASE?
        upon a model verification check
            whole VC dir                    from REAL_READ
            model dir                       from TEMP_READ

    Worker:
        upon a VC,MO job
            any dependencies (folders)      from REAL_READ
            whole VCs dir                   from REAL_READ
            MO dir                          from TEMP_READ
        upon a TE,MO
            TE dir                          from REAL_READ
            MO dir                          from REAL_READ
            required dependency dirs        from REAL_READ

WRITES
    Director:
        None I can think of
    Worker:
        upon VC,MO job completion
            VR dir                          to TEMP_WRITE
        upon TE,MO job completion
            TR dir                          to REAL_WRITE
"""

from config import *
logger = logger.getChild("rsync_tools")
import os
import subprocess, tempfile
import models

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
    """ run rsync """
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
    rsync_command(files,read=True)

def rsync_write(files):
    rsync_command(files,read=False)


def full_sync():
    """ grab the whole repository """
    rsync_read(["te/","mo/","md/","tr/","td/","vc/","vr/","pr/","rd/","database.sqlite"])

def full_write():
    """ write the whole repo """
    rsync_write(["te/","mo/","md/","tr/","td/","vc/","vr/","pr/","rd/","database.sqlite","trlookup.txt"])


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
    obj = models.KIMObject(kid)
    return kid.path

#=================================
# director methods
#=================================

def director_model_verification_read(modelname):
    """ when director needs to verify a model """
    files = ["vc/","database.sqlite"]
    files.append(kid_to_folder(modelname))
    rsync_read(files)

def director_new_model_read(modelname):
    """ when a director gets a new model """
    files = ["te/","tr/","database.sqlite"]
    files.append(kid_to_folder(modelname))
    rsync_read(files)

def director_new_test_read(testname):
    """ when a director gets a new test """
    files = ["mo/","tr/","database.sqlite"]
    files.append(kid_to_folder(testname))
    rsync_read(files)

#==================================
# worker methods
#==================================


def worker_model_verification_read(modelname,vcname,depends):
    """ when a worker needs to run a verification job """
    files = [kid_to_folder(modelname), kid_to_folder(vcname), "database.sqlite"]
    for depend in depends:
        files.append(kid_to_folder(depend))
    rsync_read(files)

def worker_test_result_read(testname,modelname,depends):
    """ when a worker needs to run a test result """
    files = [kid_to_folder(modelname),kid_to_folder(testname), "database.sqlite"]
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
