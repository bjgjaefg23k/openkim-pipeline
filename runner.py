""" 
Some scripts that let us run tests and the like
"""
import time, simplejson
from subprocess import Popen, PIPE
import repository as repo

def run_test_on_model(testname,modelname):
    """ run a test with the corresponding model, capture the output as a dict """
    
    #do a sanity check, see if the test and model exist
    if testname not in repo.KIM_TESTS:
        raise KeyError, "test <{}> not valid".format(testname)
    if modelname not in repo.KIM_MODELS:
        raise KeyError, "model <{}> not valid".format(modelname)

    #grab the executable
    executable = [repo.test_executable(testname)]
    #profiling time thing
    timeblock = ["/usr/bin/time","--format={\"_usertime\":%U,\"_memmax\":%M,\"_memavg\":%K}"]

    test_dir = repo.test_dir(testname)
    # run the test in its own directory
    with repo.in_repo_dir(test_dir):
        #grab the input file
        output_info = repo.load_info(OUTPUT_FILE)
        with open(INPUT_FILE) as fl:
            with template.process(fl) as kim_stdin:
                start_time = time.time()
                process = Popen(timeblock+ executable,stdin=PIPE,stdout=PIPE,stderr=PIPE)
                stdout, stderr = process.communicate(kim_stdin)
                end_time = time.time()

    if process.poll() is None:
        process.kill()
        raise RuntimeError, "your test didn't terminate nicely"

    data_string = stdout.splitlines()[-1]
    data = simplejson.loads(data_string)

    data = { output_info[key]:val for key,val in data.iteritems() }

    data["_testname"] = testname
    data["_modelname"] = modelname
    data["_time"] = end_time-start_time
    data["_created_at"] = time.time()
    time_str = stderr.splitlines()[-1]
    time_dat = simplejson.loads(time_str)
    data.update(time_dat)

    return data


#run all the tests on all the models
def update_repo():
    for test in repo.KIM_TESTS:
        for model in repo.models_for_test(test):
            if not repo.prediction_exists(test,model):
                print "Running {} vs {}".format(test,model)
                results = run_test_on_model(test,model)
                repo.write_result_to_file(results)
            else:
                print "{} vs {} seems current".format(test,model)

