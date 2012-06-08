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
    if not files:
        try:
            logger.info("running full rsync")
            if read:
                cmd = " ".join(["rsync",RSYNC_FLAGS, RSYNC_PATH, RSYNC_LOG_FILE_FLAG, LOCAL_REPO_ROOT])
            else:
                cmd = " ".join(["rsync",RSYNC_FLAGS, RSYNC_LOG_FILE_FLAG, LOCAL_REPO_ROOT, RSYNC_PATH])    
            return subprocess.check_call(cmd,shell=True)
        except subprocess.CalledProcessError:
            logger.error("RSYNC FAILED")
            raise
            
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

def rsync_read(*args,**kwargs):
    rsync_command(*args,read=True,**kwargs)

def rsync_write(*args,**kwargs):
    rsync_command(*args,read=False,**kwargs)


def full_sync():
    """ grab the whole repository """


def temp_write(*args):
    """ write things to the temporary write area """

def temp_read(*args):
    """ pull things from the temporary read area """

def real_write(*args):
    """ FORBIDDEN:
        write things to the real write area """

def real_read(*args):
    """ read things from the real read directory """

#=================================
# director methods
#=================================

def director_model_verification_read(modelname):
    """ when director needs to verify a model """
    rsync_read(["vc/","mo/{}/".format(modelname)])

def director_new_model_read(modelname):
    """ when a director gets a new model """
    rsync_read(["mo/{}/".format(modelname), "te/", "tr/" ])

def director_new_test_read(testname):
    """ when a director gets a new test """
    rsync_read(["mo/","te/{}/".format(testname), "tr/" ] )

#==================================
# worker methods
#==================================


def worker_model_verification_read(modelname,vcname,depends):
    """ when a worker needs to run a verification job """
    files = ["mo/{}/".format(modelname),"vc/{}/".format(vcname)]
    for depend in depends:
        leader,pk,version = kimid.parse_kimid(depend)
        files.append(leader.lower() + "/" + depend + "/" )
    rsync_read(files)

def worker_test_result_read(testname,modelname,depends):
    """ when a worker needs to run a test result """
    files = ["mo/{}/".format(modelname),"te/{}/".format(testname)]
    for depend in depends:
        leader,pk,version = kimid.parse_kimid(depend)
        files.append(leader.lower() + "/" + depend + "/")
    rsync_read(files)

def worker_model_verification_write(vrname):
    """ when a worker ran a model verification """
    files = ["vr/{}/".format(vrname)]
    rsync_write(files)

def worker_test_result_write(trname):
    """ when a worker ran a test result """
    files = ["tr/{}/".format(trname)]
    rsync_write(files)
