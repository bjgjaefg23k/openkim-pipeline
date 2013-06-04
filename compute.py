"""
Some scripts that let us run tests and the like

"""
import os
import sys
import time
import simplejson
import signal
import itertools
from config import *
from logger import logging
logger = logging.getLogger("pipeline").getChild("compute")

import kimobjects
import subprocess, threading
import yaml
import shutil
from contextlib import contextmanager

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


#================================================================
# the actual computation class
#================================================================
class Computation(object):
    def __init__(self, runner=None, subject=None):
        self.runner = runner
        self.subject = subject
        self.runner_temp = runner
        self.runtime = None
        self.results = None

    def _create_tempdir(self, trcode):
        tempname = self.runner.kim_code_name+"_running"+trcode+"__"+self.runner.kim_code_id
        self.runner_temp = kimobjects.kim_obj(self.runner.kim_code, search=False, subdir=tempname)
        shutil.copytree(self.runner.path, self.runner_temp.path)

    def _delete_tempdir(self):
        shutil.rmtree(self.runner_temp.path)

    @contextmanager
    def tempdir(self, trcode):
        if trcode:
            self._create_tempdir(trcode)
        
            cwd = os.getcwd()
            os.chdir(self.runner_temp.path)

        try:
            yield
        except Exception as e:
            logger.error("%r" % e)
            raise e
        finally:
            if trcode:
                os.chdir(cwd)
                self._delete_tempdir()

    def execute_in_place(self):
        """ Execute a test with a corresponding model
        with /usr/bin/time profilling where ever the test exists
        """
        logger.info("running %r with %r",self.runner,self.subject)
    
        executable = self.runner_temp.executable
        timeblock = "/usr/bin/time --format={\\\"usertime\\\":%U,\\\"memmax\\\":%M,\\\"memavg\\\":%K} "
    
        # run the test in its own directory
        with self.runner_temp.in_dir():
            with self.runner_temp.processed_infile(self.subject) as kim_stdin_file, open(STDOUT_FILE,'w') as stdout_file, open(STDERR_FILE,'w') as stderr_file:
                start_time = time.time()
                process = Command(timeblock+executable,stdin=kim_stdin_file,stdout=stdout_file,stderr=stderr_file)
                logger.info("launching run...")
                try:
                    retcode = process.run(timeout=RUNNER_TIMEOUT)
                except PipelineTimeout:
                    logger.error("test %r timed out",self.runner)
                    raise PipelineTimeout, "your test timed out"
    
                end_time = time.time()
    
        # It seems the test didn't finish
        if process.poll() is None:
            process.kill()
            raise KIMRuntimeError, "your test didn't terminate nicely"
    
        elapsed = end_time - start_time
        logger.info("run completed in %r seconds" % elapsed)
        if retcode != 0:
            logger.error("test returned error code %r, %r" % (retcode, os.strerror(retcode)) )
        self.runtime = elapsed
        return elapsed, retcode

    def process_output(self, trcode=None, extrainfo=None):
        """ Template the run results into the proper YAML
        """
        with self.runner_temp.in_dir(), open(STDOUT_FILE) as stdout_file:
            stdout = stdout_file.read()

        # Try to find the first valid bit of json looking backwards in the output.
        logger.debug('Searching for JSON output...')
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
            last_out, last_err = last_output_lines(self.runner_temp, STDOUT_FILE, STDERR_FILE)
            raise PipelineTemplateError, "Test didn't return JSON! \n<<STDOUT: \n%s>> \n<<STDERR: \n%s>>" % (last_out, last_err)

        logger.debug('Found JSON:\n{}'.format(simplejson.dumps(data,indent=4)))
        self.results = data

        #Add output
        pipelineinfo = {"kim-template-tags": ["pipeline-info"]}
        pipelineinfo['test-extended-id']  = self.runner.kim_code
        pipelineinfo['model-extended-id']  = self.subject.kim_code
        pipelineinfo['test-result-extended-id']  = trcode
        pipelineinfo['output'] = simplejson.dumps(data)

        # Add metadata
        pipelineinfo['info'] = {}
        info_dict = pipelineinfo['info']
        info_dict["kimlog"] = "@FILE[{}]".format(KIMLOG_FILE)
        info_dict["stdout"] = "@FILE[{}]".format(STDOUT_FILE)
        info_dict["time"] = self.runtime 
        info_dict["created-at"] = time.time()
        info_dict["vmversion"] = os.environ["VMVERSION"]

        if extrainfo:
            info_dict.update(extrainfo)

        # get the information from the timing script
        with self.runner_temp.in_dir(), open(STDERR_FILE) as stderr_file:
            stderr = stderr_file.read()
        time_str = stderr.splitlines()[-1]
        time_dat = simplejson.loads(time_str)
        info_dict.update(time_dat)

        logger.debug("Added metadata:\n{}".format(simplejson.dumps(info_dict,indent=4)))

        renderedyaml = self.runner_temp.template.render(**data)
        logger.debug("Manipulated template:\n{}".format(renderedyaml))
        with self.runner_temp.in_dir(), open(TEMPLATE_OUT,'w') as f:
            f.write(renderedyaml)

        tryaml = list(yaml.load_all(renderedyaml))
        logger.debug("Formed dict:\n{}".format("\n".join([simplejson.dumps(temp,indent=4) for temp in tryaml])))

        documents = [pipelineinfo]
        documents.extend(tryaml)

        logger.debug("got data %r",data)
        with self.runner_temp.in_dir(), open(TR_OUTPUT,'w') as f:
            f.write(yaml.dump_all(documents, default_flow_style=False, explicit_start=True))


    def write_result(self, trcode=None):
        if not trcode:
            logger.info("no result code provided, leaving in %r", self.runner_temp.path)
            return 

        result = kimobjects.TestResult(kim_code=trcode, search=False) 
        shutil.rmtree(result.path)

        p1 = os.path.join(self.runner_temp.path, TR_OUTPUT)
        p2 = os.path.join(self.runner_temp.path, trcode)
        shutil.copy2(p1, p2)

        shutil.copytree(self.runner_temp.path, result.path)

    def run(self, trcode=None, extrainfo=None):
        """
        run a test with the corresponding model, with /usr/bin/time profilling,
        capture the output as a dict, and return or
        run a V{T,M} with the corresponding {TE,MO}

        if trcode is set, then run in a temporary directory, otherwise local run
        """
        with self.tempdir(trcode):
            self.execute_in_place()
            self.process_output(trcode, extrainfo)
            self.write_result(trcode)


#================================================================
# helper functions
#================================================================
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


