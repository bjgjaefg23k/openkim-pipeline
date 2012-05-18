"""
Contains routines for running tests against models and vice versa
"""

import repository as repo
from subprocess import Popen, PIPE
import simplejson


def run_test_on_model(testname,modelname):
    """ run a test with the corresponding model, capture the output as a dict """
    if testname not in repo.KIM_TESTS:
        raise KeyError, "test <{}> not valid".format(testname)
    if modelname not in repo.KIM_MODELS:
        raise KeyError, "model <{}> not valid".format(modelname)

    executable = repo.test_executable(testname)
    process = Popen(executable,stdin=PIPE,stdout=PIPE)
    stdout, stderr = process.communicate(modelname)

    if process.poll() is None:
        process.kill()
        raise RuntimeError, "your test didn't terminate nicely"

    data_string = stdout.splitlines()[-1]
    return simplejson.loads(data_string)



