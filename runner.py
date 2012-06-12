"""
Some scripts that let us run tests and the like
"""
import time, simplejson, signal, itertools, sys
from subprocess import Popen, PIPE
import repository as repo
from config import *
logger = logger.getChild("runner")
import template


def timeout_handler(signum, frame):
    raise PipelineTimeout()


def outfile_to_dict(outfile):
    outdata = open(outfile).read()
    lines = outdata.splitlines()
    data = {}
    for line in lines:
        front,back = line.split(":")
        data.update({ front.strip(): back.strip()})
    return data

def line_filter(line):
    return bool(line.strip())

def run_test_on_model(testname,modelname):
    """ run a test with the corresponding model, capture the output as a dict """
    logger.info("running %r with %r",testname,modelname)
    #do a sanity check, see if the test and model exist
    if testname not in repo.KIM_TESTS:
        logger.error("test %r not valid",testname)
        raise PipelineFileMissing, "test <{}> not valid".format(testname)
    if modelname not in repo.KIM_MODELS:
        logger.error("model %r not valid",modelname)
        raise PipelineFileMissing, "model <{}> not valid".format(modelname)

    #grab the executable
    executable = [repo.test_executable(testname)]
    #profiling time thing
    timeblock = ["/usr/bin/time","--format={\"_usertime\":%U,\"_memmax\":%M,\"_memavg\":%K}"]

    test_dir = repo.test_dir(testname)
    # run the test in its own directory
    with repo.in_repo_dir(test_dir):
        #grab the input file
        output_info = outfile_to_dict(OUTPUT_FILE)
        with open(INPUT_FILE) as fl:
            with template.process(fl,modelname,testname) as kim_stdin_file:
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

    data = { output_info[key]:val for key,val in data.iteritems() }
    data["_stdout"] = "@FILE[{}]".format(STDOUT_FILE)
    data["_testname"] = testname
    data["_modelname"] = modelname
    data["_time"] = end_time-start_time
    data["_created_at"] = time.time()
    time_str = stderr.splitlines()[-1]
    time_dat = simplejson.loads(time_str)
    data.update(time_dat)

    logger.debug("got data %r",data)
    return data


#run all the tests on all the models
def update_repo(force=False):
    logger.info("attempting to update repo...")
    for test in repo.KIM_TESTS:
        #logger.info("attempting to update test %r",test)
        for model in repo.models_for_test(test):
            if force or not repo.test_result_exists(test,model):
                logger.info("Running %r vs %r",test,model)

                try:
                    results = run_test_on_model(test,model)
                    repo.write_result_to_file(results, None)
                except:
                    logger.error("WE HAD an error on (%r,%r) with:\n%r",test,model,sys.exc_info()[0])
            else:
                logger.info("%r vs %r seems current",test,model)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "update":
            update_repo()
