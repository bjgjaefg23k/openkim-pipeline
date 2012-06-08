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

#================================
# rsync wrappers 
#================================

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

def director_new_model_read(modelname):
    """ when a director gets a new model """

def director_new_test_read(testname):
    """ when a director gets a new test """

#==================================
# worker methods
#==================================


def worker_model_verification_read(modelname,vcname,depends):
    """ when a worker needs to run a verification job """

def worker_test_result_read(testname,modelname,depends):
    """ when a worker needs to run a test result """

def worker_model_verification_write(vrname):
    """ when a worker ran a model verification """

def worker_test_result_write(trname):
    """ when a worker ran a test result """
