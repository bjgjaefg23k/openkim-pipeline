""" 
Some scripts that let us run tests and the like
"""
import time, simplejson
from subprocess import Popen, PIPE
import repository as repo

def run_test_on_model(testname,modelname):
    """ run a test with the corresponding model, capture the output as a dict """
    if testname not in repo.KIM_TESTS:
        raise KeyError, "test <{}> not valid".format(testname)
    if modelname not in repo.KIM_MODELS:
        raise KeyError, "model <{}> not valid".format(modelname)

    executable = repo.test_executable(testname)
    
    start_time = time.time()
    process = Popen(executable,stdin=PIPE,stdout=PIPE)
    stdout, stderr = process.communicate(modelname)
    end_time = time.time()

    if process.poll() is None:
        process.kill()
        raise RuntimeError, "your test didn't terminate nicely"

    data_string = stdout.splitlines()[-1]
    data = simplejson.loads(data_string)
    data["_testname"] = testname
    data["_modelname"] = modelname
    data["_time"] = end_time-start_time

    return data

