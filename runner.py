"""
Some scripts that let us run tests and the like

"""
import time, simplejson, signal, itertools, sys
from subprocess import Popen, PIPE
from config import *
logger = logger.getChild("runner")
import os
import models


def timeout_handler(signum, frame):
    raise PipelineTimeout()


def line_filter(line):
    return bool(line.strip())

def run_test_on_model(test,model):
    """ run a test with the corresponding model, 
    with /usr/bin/time profilling,
    capture the output as a dict, and return """
    logger.info("running %r with %r",test,model)

    #grab the executable
    executable = [test.executable]
    #profiling time thing
    timeblock = ["/usr/bin/time","--format={\"_usertime\":%U,\"_memmax\":%M,\"_memavg\":%K}"]

    test_dir = test.path
    # run the test in its own directory
    with test.in_dir():
        #grab the input file
        output_info = test.out_dict
        with test.processed_infile(model) as kim_stdin_file:
            kim_stdin = kim_stdin_file.read()
            start_time = time.time()
            process = Popen(timeblock+ executable,stdin=PIPE,stdout=PIPE,stderr=PIPE)
            logger.info("launching run...")
            try:
                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(RUNNER_TIMEOUT)
                try:
                    stdout, stderr = process.communicate(kim_stdin)
                finally:
                    signal.signal(signal.SIGALRM, old_handler)
                signal.alarm(0)
            except PipelineTimeout:
                logger.error("test %r timed out",testname)
                raise PipelineTimeout, "your test timed out"

            end_time = time.time()
            with open(STDOUT_FILE,"w") as stdout_file:
                stdout_file.write(stdout)

    # It seems the test didn't finish
    # this probably doesn't end
    if process.poll() is None:
        process.kill()
        raise KIMRuntimeError, "your test didn't terminate nicely"

    #look backwards in the stdout for the first non whitespaced line
    try:
        data_string = next(itertools.ifilter(line_filter,reversed(stdout.splitlines())))
        logger.debug("we have a data_string: %r",data_string)
    except StopIteration:
        #there was no output
        #likely a kim error
        logger.error("We probably had a KIM error")
        raise KIMRuntimeError
    try:
        data = simplejson.loads(data_string)
    except simplejson.JSONDecodeError:
        logger.error("We didn't get JSON back!")
        raise PipelineTemplateError, "test didn't return JSON"
    
    #GET METADATA
    data = { output_info[key]:val for key,val in data.iteritems() }
    data["_kimlog"] = "@FILE[{}]".format(KIMLOG_FILE)
    data["_stdout"] = "@FILE[{}]".format(STDOUT_FILE)
    data["_testname"] = test.kim_code
    data["_modelname"] = model.kim_code
    data["_time"] = end_time-start_time
    data["_created_at"] = time.time()
    data["_vmversion"] = os.environ["VMVERSION"]

    # get the information from the timing script
    time_str = stderr.splitlines()[-1]
    time_dat = simplejson.loads(time_str)
    data.update(time_dat)

    logger.debug("got data %r",data)
    return data


#run all the tests on all the models
def update_repo(force=False):
    """ Attempt to run all valid matching test and model pairs,
    meant to be used locally as a test.
    """
    logger.info("attempting to update repo...")
    for test in models.Test.all():
        #logger.info("attempting to update test %r",test)
        for model in test.models:
            if force or not models.TestResult.test_result_exists(test,model):
                logger.info("Running %r vs %r",test,model)
                try:
                    results = run_test_on_model(test,model)
                    tr = models.TestResult(results=results)
                except:
                    logger.error("WE HAD an error on (%r,%r) with:\n%r",test,model,sys.exc_info()[0])
            else:
                logger.info("%r vs %r seems current",test,model)


#run all the tests on all the models
def update_repo_all(force=False):
    """ Run all tests and models against one another, without first checking matches with KIM_API_init,
    meant to be used locally as a test
    """
    logger.info("attempting to update repo...")
    for model in models.Model.all():
        for test in models.Test.all():
            #logger.info("attempting to update test %r",test)
            if force or not models.TestResult.test_result_exists(test,model):
                logger.info("Running %r vs %r",test,model)
                try:
                    results = run_test_on_model(test,model)
                    tr = models.TestResult(results=results)
                except:
                    logger.error("WE HAD an error on (%r,%r) with:\n%r",test,model,sys.exc_info()[0])
            else:
                logger.info("%r vs %r seems current",test,model)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "update":
            update_repo()
        elif sys.argv[1] == "updateall":
            update_repo_all()
