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
import kimunits
import clj
import json

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

    def _clean_old_run(self):
        for flname in INTERMEDIATE_FILES:
            try:
                os.remove(flname)
            except OSError as e:
                pass

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
            self._clean_old_run()
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

    def process_output(self):
        """ Template the run results into the proper YAML """
        # Short-circuit if we already have a results.edn
        with self.runner_temp.in_dir():
            if not os.path.isfile(RESULT_FILE):
                raise KIMRuntimeError, "The test did not produce a %s output file." % RESULT_FILE

        # now, let's check whether that was actual a valid test result
        logger.debug("Checking the output EDN for validity")
        with self.runner_temp.in_dir(), open(RESULT_FILE, 'r') as f:
            try:
                doc = clj.load(f)
            except Exception as e:
                raise KIMRuntimeError, "Test did not produce valid EDN %s" % RESULT_FILE

            try:
                # insert units business
                logger.debug("Attempting to add unit conversions...")
                try:
                    newdoc = kimunits.add_si_units(doc)
                except kimunits.UnitConversion as e:
                    logger.error("Error in Unit Conversion")
                    raise PipelineTemplateError("Error in unit conversions")
            except Exception as e:
                logger.error("Templated %r did not render valid YAML." % TEMPLATE_FILE)
                raise PipelineTemplateError("Improperly formatted YAML after templating")

        with self.runner_temp.in_dir(), open(RESULT_FILE, 'w') as f:
            logger.debug("Writing unit converted version")
            json.dump(newdoc, f, separators=(" "," "), indent=4)

        logger.debug("Made it through YAML read, everything looks good")


    def gather_profiling_info(self, extrainfo=None):
        # Add metadata
        info_dict = {}
        info_dict["time"] = self.runtime
        info_dict["created-at"] = time.time()
        if extrainfo:
            info_dict.update(extrainfo)

        # get the information from the timing script
        with self.runner_temp.in_dir():
            if os.path.exists(STDERR_FILE):
                with open(STDERR_FILE) as stderr_file:
                    stderr = stderr_file.read()
                time_str = stderr.splitlines()[-1]
                time_dat = simplejson.loads(time_str)
                info_dict.update(time_dat)

        logger.debug("Added metadata:\n{}".format(simplejson.dumps(info_dict,indent=4)))

        logger.debug("Caching profile information")
        self.info_dict = info_dict


    def write_result(self, error=False):
        if error:
            self.result_path = os.path.join("er", self.result_code)
            self.full_result_path = os.path.join(KIM_REPOSITORY_DIR, self.result_path)

        logger.debug("Copying kim.log")
        with self.runner_temp.in_dir():
            if os.path.exists("./kim.log"):
                shutil.copy2("./kim.log", KIMLOG_FILE)

        # create the kimspec.yaml file for the test results
        logger.debug("Create %s file" % CONFIG_FILE)
        kimspec = {}
        kimspec[self.runner.runner_name] = self.runner.kim_code
        kimspec[self.subject.subject_name] = self.subject.kim_code
        kimspec['domain'] = 'openkim.org'

        pipelinespec = {}
        if self.info_dict:
            pipelinespec['profiling'] = self.info_dict
        if self.result_code:
            pipelinespec['UUID'] = self.result_code

        with self.runner_temp.in_dir(), open(os.path.join(OUTPUT_DIR,CONFIG_FILE),'w') as f:
            yaml.dump(kimspec, f, default_flow_style=False)
        with self.runner_temp.in_dir(), open(os.path.join(OUTPUT_DIR,PIPELINESPEC_FILE),'w') as f:
            yaml.dump(pipelinespec, f, default_flow_style=False)

        logger.debug("Result path = %s", self.full_result_path)
        outputdir = os.path.join(self.runner_temp.path,OUTPUT_DIR)

        # short circuit moving over the result tree if we have not trcode
        if not self.result_code:
            logger.info("No TR code provided, leaving in %s", outputdir)
            return

        # copy over the entire tree if it is done
        logger.info("Copying the contents of %s to %s", outputdir, self.full_result_path)
        try:
            shutil.rmtree(self.full_result_path)
        except OSError:
            pass
        finally:
            shutil.copytree(outputdir, self.full_result_path)


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
                self.process_output()
                self.gather_profiling_info(extrainfo)
                self.write_result(error=False)
            except Exception as e:
                import traceback
                trace = traceback.format_exc()

                self.gather_profiling_info(extrainfo)
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

