"""
Some scripts that let us run tests and the like

"""
import os
import sys
import time
import simplejson
import signal
import itertools
import subprocess, threading
import yaml
import shutil
from contextlib import contextmanager
import ConfigParser

from config import *
import kimobjects
from logger import logging
logger = logging.getLogger("pipeline").getChild("compute")


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

        # be sure to grab the returncode (poll is to activate it)
        self.process.poll()
        return self.process.returncode

    def poll(self):
        return self.process.poll()

    def terminate(self):
        return self.process.terminate()


#================================================================
# the actual computation class
#================================================================
class Computation(object):
    def __init__(self, runner=None, subject=None, result_code=""):
        self.runner = runner
        self.subject = subject
        self.runner_temp = runner
        self.runtime = None
        self.results = None
        self.result_code = result_code
        self.info_dict = None

        self.result_path = os.path.join(self.runner_temp.result_leader.lower(), self.result_code)
        self.full_result_path = os.path.join(KIM_REPOSITORY_DIR, self.result_path)

    def _create_tempdir(self):
        tempname = self.runner.kim_code_name+"_running"+self.result_code+"__"+self.runner.kim_code_id
        self.runner_temp = kimobjects.kim_obj(self.runner.kim_code, search=False, subdir=tempname)
        shutil.copytree(self.runner.path, self.runner_temp.path)

    def _create_output_dir(self):
        outputdir = os.path.join(self.runner_temp.path,OUTPUT_DIR)
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)

    def _delete_tempdir(self):
        shutil.rmtree(self.runner_temp.path)

    @contextmanager
    def tempdir(self):
        if self.result_code:
            self._create_tempdir()

            cwd = os.getcwd()
            os.chdir(self.runner_temp.path)

        try:
            self._create_output_dir()
            yield
        except Exception as e:
            logger.error("%r" % e)
            raise e
        finally:
            if self.result_code:
                os.chdir(cwd)
                self._delete_tempdir()

    def execute_in_place(self):
        """ Execute a runner with a corresponding subject
        with /usr/bin/time profilling where ever the executable exists
        """
        logger.info("running %r with %r",self.runner,self.subject)

        executable = self.runner_temp.executable
        libc_redirect = "LIBC_FATAL_STDERR_=1 "
        timeblock = "/usr/bin/time --format={\\\"usertime\\\":%U,\\\"memmax\\\":%M,\\\"memavg\\\":%K} "

        # run the runner in its own directory
        with self.runner_temp.in_dir():
            with self.runner_temp.processed_infile(self.subject) as kim_stdin_file,  \
                    open(STDOUT_FILE,'w') as stdout_file, \
                    open(STDERR_FILE,'w') as stderr_file:
                start_time = time.time()

                logger.info("launching run...")
                process = Command(libc_redirect+timeblock+executable,stdin=kim_stdin_file,
                        stdout=stdout_file,stderr=stderr_file)

                try:
                    self.retcode = process.run(timeout=RUNNER_TIMEOUT)
                except PipelineTimeout:
                    logger.error("runner %r timed out",self.runner)
                    raise PipelineTimeout, "your executable timed out at %r hours" % (RUNNER_TIMEOUT / 3600)

                end_time = time.time()

        # It seems the runner didn't finish
        if process.poll() is None:
            process.kill()
            raise KIMRuntimeError, "Your test did not respond to timeout request and did not exit"

        self.runtime = end_time - start_time
        logger.info("Run completed in %r seconds" % self.runtime)
        if self.retcode != 0:
            logger.error("Runner returned error code %r, %r" % (self.retcode, os.strerror(self.retcode)) )
            raise KIMRuntimeError("Executable %r returned error code %r" % (self.runner_temp, self.retcode))

    def process_output(self, extrainfo=None):
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
            logger.exception("We didn't get JSON back!")
            raise PipelineTemplateError, "Test didn't return JSON!"

        logger.debug('Found JSON:\n{}'.format(simplejson.dumps(data,indent=4)))
        self.results = data

        # Add metadata
        info_dict = {}
        info_dict["time"] = self.runtime
        info_dict["created-at"] = time.time()
        if extrainfo:
            info_dict.update(extrainfo)

        # get the information from the timing script
        with self.runner_temp.in_dir(), open(STDERR_FILE) as stderr_file:
            stderr = stderr_file.read()
        time_str = stderr.splitlines()[-1]
        time_dat = simplejson.loads(time_str)
        info_dict.update(time_dat)

        logger.debug("Added metadata:\n{}".format(simplejson.dumps(info_dict,indent=4)))

        #safeify data, escape the strings
        safe_data = { k:v.encode('string_escape') for k,v in data.iteritems() if isinstance(v,str) }
        renderedyaml = self.runner_temp.template.render(**safe_data)
        logger.debug("Manipulated template:\n{}".format(renderedyaml))
        logger.debug("Writing output.")
        with self.runner_temp.in_dir(), open(RESULT_FILE,'w') as f:
            f.write(renderedyaml)

        logger.debug("caching profile information")
        self.info_dict = info_dict

        logger.debug("Copying kim.log")
        with self.runner_temp.in_dir():
            if os.path.exists("./kim.log"):
                shutil.copy2("./kim.log", KIMLOG_FILE)


    def write_result(self, error=False):
        if error:
            self.result_path = os.path.join("er", self.result_code)
            self.full_result_path = os.path.join(KIM_REPOSITORY_DIR, self.result_path)

        logger.debug("Create kimspec.ini file")
        config = ConfigParser.ConfigParser()
        config.optionxform = str
        config.add_section('kimspec')
        if self.result_code:
            config.set('kimspec','UUID',self.result_code)
        config.set('kimspec',self.runner.runner_name,self.runner.kim_code)
        config.set('kimspec',self.subject.subject_name,self.subject.kim_code)
        if self.info_dict:
            config.add_section('profiling')
            for key,value in self.info_dict.iteritems():
                config.set('profiling',key,value)

        with self.runner_temp.in_dir(), open(os.path.join(OUTPUT_DIR,CONFIG_FILE),'w') as f:
            config.write(f)

        if not self.result_code:
            logger.info("No TR code provided, leaving in %s", os.path.join(self.runner_temp.path, OUTPUT_DIR))
            return

        mesg = "Result" if not error else "Error"
        logger.debug("%s path = %s", mesg, self.full_result_path)
        outputdir = os.path.join(self.runner_temp.path,OUTPUT_DIR)

        logger.info("Copying the contents of %s to %s", outputdir, self.full_result_path)
        try:
            shutil.rmtree(self.full_result_path)
        except OSError:
            pass
        finally:
            shutil.copytree(os.path.join(self.runner_temp.path,OUTPUT_DIR), self.full_result_path)

    def run(self, extrainfo=None):
        """
        run a runner with the corresponding subject, with /usr/bin/time profilling,
        capture the output as a dict, and return or
        run a V{T,M} with the corresponding {TE,MO}

        if result_code is set, then run in a temporary directory, otherwise local run
        """
        with self.tempdir():
            try:
                self.execute_in_place()
                self.process_output(extrainfo)
                self.write_result(error=False)
            except Exception as e:
                import traceback
                trace = traceback.format_exc()

                self.write_result(error=True)

                files = [STDOUT_FILE, STDERR_FILE, KIMLOG_FILE]
                tails = last_output_lines(self.runner_temp, files)

                outs = trace+"\n"
                for f, t in zip(files, tails):
                    outs += f+":\n"
                    outs += "".join(["-"]*(len(f)+1))+"\n"
                    outs += append_newline(t)+"\n"
                raise PipelineRuntimeError(e, outs)

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
    except Exception as e:
        lines = [""]
    return "".join(lines)

def last_output_lines(kimobj, files, n=20):
    with kimobj.in_dir():
        tails = [ tail(f, n) for f in files ]
    return tails

def append_newline(string):
    if len(string) > 0 and string[-1] != '\n':
        string += "\n"
    return string
