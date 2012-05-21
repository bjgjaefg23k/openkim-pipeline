""" 
Some scripts that let us run tests and the like
"""


def run_test_on_model(self,testname,modelname):
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


