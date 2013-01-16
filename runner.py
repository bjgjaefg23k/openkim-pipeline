"""
Some scripts that let us run tests and the like

"""
import time, simplejson, signal, itertools, sys
from config import *
logger = logger.getChild("runner")
import os
import kimobjects
import subprocess, threading

#================================================================
# helper functions
#================================================================
def timeout_handler(signum, frame):
    raise PipelineTimeout()

def getboxinfo():
    os.system("cd /home/vagrant/openkim-pipeline; git log -n 1 | grep commit | sed s/commit\ // > /persistent/setuphash")

    info = {}
    things = ['sitename','username','boxtype','ipaddr','vmversion','setuphash']

    for thing in things:
        info[thing] = open(os.path.join('/persistent',thing)).read().strip()
    return info

def line_filter(line):
    return bool(line.strip())

def tail(f, n=5):
    try:
        stdin,stdout = os.popen2("tail -n "+str(n)+" "+f)
        stdin.close()
        lines = stdout.readlines();
        stdout.close()
    except:
        lines = ["<NONE>"]
    return "".join(lines)

def last_output_lines(test, stdout, stderr):
    with test.in_dir():
        return tail(stdout), tail(stderr)

def run_critical_verifiers(kimobj):
    vt = ["Build__VT_000000000000_000",
          "FilenamesPath__VT_000000000001_000",
          "PipelineAPI__VT_000000000002_000",
          "TemplateCheck__VT_000000000003_000"]
    vm = ["Build__VM_000000000000_000",
          "FilenamesPath__VM_000000000001_000",
          "PipelineAPI__VM_000000000002_000"]
   
    if isinstance(kimobj, models.Test):
        verifiers = vt
    elif isinstance(kimobj, models.Model):
        verifiers = vm
    else:
        return

    passed = []
    for v in verifiers:
        try:
            data = run_test_on_model(models.Verifier(v), kimobj)
        except Exception as e:
            data = {}
            data['pass'] = False
        passed.append(data['pass']) 
    return verifiers,passed


#================================================================
# a class to be able to timeout on a command
#================================================================
class Command(object):
    def __init__(self, cmd, stdin=None, stdout=None, stderr=None):
        self.cmd = cmd
        self.process = None
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def run(self, timeout):
        def target():
            self.process = subprocess.Popen(self.cmd, stdin=self.stdin, stdout=self.stdout, stderr=self.stderr, shell=True)
            self.process.communicate()

        thread = threading.Thread(target=target)
        thread.start()

        thread.join(timeout)
        if thread.is_alive():
            self.process.terminate()
            thread.join()
            raise PipelineTimeout
        return self.process.returncode

    def poll(self):
        return self.process.poll()

    def terminate(self):
        return self.process.terminate()


#=============================================================
# the real meat and cheese of this file
#=============================================================
def execute_test_on_model(test,model):
    """ Execute a test with a corresponding model
    with /usr/bin/time profilling
    """
    logger.info("running %r with %r",test,model)

    #grab the executable
    executable = test.executable
    #profiling time thing
    timeblock = "/usr/bin/time --format={\\\"usertime\\\":%U,\\\"memmax\\\":%M,\\\"memavg\\\":%K} "

    test_dir = test.path
    # run the test in its own directory
    with test.in_dir():
        # So, I switched this to now use the file handlers in the popen command
        # directly in the hopes that this will prevent issues of the buffer not
        # clearing when a test with a lot of output is run.
        with test.processed_infile(model) as kim_stdin_file, open(STDOUT_FILE,'w') as stdout_file, open(STDERR_FILE,'w') as stderr_file:
            #grab the input file
            # output_info = test.out_dict
            start_time = time.time()
            process = Command(timeblock+ executable,stdin=kim_stdin_file,stdout=stdout_file,stderr=stderr_file)
            logger.info("launching run...")
            try:
                process.run(timeout=RUNNER_TIMEOUT)
            except PipelineTimeout:
                logger.error("test %r timed out",test)
                raise PipelineTimeout, "your test timed out"

            end_time = time.time()

    # It seems the test didn't finish
    # this probably doesn't end
    if process.poll() is None:
        process.kill()
        raise KIMRuntimeError, "your test didn't terminate nicely"

    return (end_time - start_time)


def run_test_on_model(test,model):
    """
    run a test with the corresponding model,
    with /usr/bin/time profilling,
    capture the output as a dict, and return
                 OR
    run a V{T,M} with the corresponding {TE,MO}
    """

    # execute test
    run_time = execute_test_on_model(test,model)

    with test.in_dir(), open(STDOUT_FILE) as stdout_file:
        stdout = stdout_file.read()

    #look backwards in the stdout for the first non whitespaced line
    #try:
    #    data_string = next(itertools.ifilter(line_filter,reversed(stdout.splitlines())))
    #    logger.debug("we have a data_string: %r",data_string)
    #except StopIteration:
    #    #there was no output, likely a kim error
    #    logger.error("We probably had a KIM error")
    #    raise KIMRuntimeError, "No output was present after completion."
    #try:
    #    data = simplejson.loads(data_string)
    #except simplejson.JSONDecodeError:
    #    logger.error("We didn't get JSON back!")
    #    last_out, last_err = last_output_lines(test, STDOUT_FILE, STDERR_FILE)
    #    raise PipelineTemplateError, "Test didn't return JSON! \n<<STDOUT: \n%s>> \n<<STDERR: \n%s>>" % (last_out, last_err)
    logger.info("Run completed, searching for output...")

    # Try to find the first valid bit of json looking backwards in the output.
    logger.debug('Finding JSON output...')
    data = None
    for data_string in itertools.ifilter(line_filter, reversed(stdout.splitlines())):
        try:
            data = simplejson.loads(data_string)
            if isinstance(data, dict):
                break
            else:
                data = None
        except simplejson.JSONDecodeError:
            continue

    if data is None:
        # We couldn't find any valid JSON
        logger.error("We didn't get JSON back!")
        last_out, last_err = last_output_lines(test, STDOUT_FILE, STDERR_FILE)
        raise PipelineTemplateError, "Test didn't return JSON! \n<<STDOUT: \n%s>> \n<<STDERR: \n%s>>" % (last_out, last_err)

    logger.debug('Found JSON:\n{}'.format(simplejson.dumps(data,indent=4)))

    #Add output
    tr_out = {}
    tr_out['output'] = data

    # Add metadata
    tr_out['info'] = {}
    info_dict = tr_out['info']
    info_dict["kimlog"] = "@FILE[{}]".format(KIMLOG_FILE)
    info_dict["stdout"] = "@FILE[{}]".format(STDOUT_FILE)
    info_dict["testname"] = test.kim_code
    info_dict["modelname"] = model.kim_code
    info_dict["time"] = run_time
    info_dict["created_at"] = time.time()
    info_dict["vmversion"] = os.environ["VMVERSION"]
    info_dict.update(getboxinfo())

    # get the information from the timing script
    with test.in_dir(), open(STDERR_FILE) as stderr_file:
        stderr = stderr_file.read()
    time_str = stderr.splitlines()[-1]
    time_dat = simplejson.loads(time_str)
    info_dict.update(time_dat)

    logger.debug("Added metadata:\n{}".format(simplejson.dumps(info_dict,indent=4)))

    #populate proper TR
    template = test.template
    vals = {'MODELNAME':model.kim_code, 'TESTNAME': test.kim_code , 'TRCODE':'@@TRCODE@@' }
    vals.update(data)
    trform = template.render(**vals)
    logger.debug("Manipulated template:\n{}".format(trform))
    with test.in_dir(), open(TEMPLATE_OUT,'w') as f:
        f.write(trform)

    trdict = simplejson.loads(trform)
    logger.debug("Formed dict:\n{}".format(simplejson.dumps(trdict,indent=4)))
    tr_out.update(trdict)

    logger.debug("got data %r",data)
    with test.in_dir(), open(TR_OUTPUT,'w') as f:
        f.write(simplejson.dumps(tr_out, indent=4))

    #Add kim_id_test, kim_id_model, validation_schema
    if isinstance(test, kimobjects.Test):
        schema_type = 'schema_tr'
    else:
        schema_type = 'schema_vr'

    tr_out.update({
        'kim_id_test': test.kim_code,
        'kim_id_model': model.kim_code,
        'validation_schema': schema_type}
        )

    # TODO: We need to inject 'kim_id' before writing
    return tr_out


#run all the tests on all the models
def update_repo(force=False):
    """ Attempt to run all valid matching test and model pairs,
    meant to be used locally as a test.
    """
    logger.info("attempting to update repo...")
    for test in kimobjects.Test.all():
        #logger.info("attempting to update test %r",test)
        for model in test.models:
            if force or not kimobjects.TestResult.test_result_exists(test,model):
                logger.info("Running %r vs %r",test,model)
                try:
                    results = run_test_on_model(test,model)
                    tr = kimobjects.TestResult(results=results)
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
    for model in kimobjects.Model.all():
        for test in kimobjects.Test.all():
            #logger.info("attempting to update test %r",test)
            if force or not kimobjects.TestResult.test_result_exists(test,model):
                logger.info("Running %r vs %r",test,model)
                try:
                    results = run_test_on_model(test,model)
                    tr = kimobjects.TestResult(results=results)
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
