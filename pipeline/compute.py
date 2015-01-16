"""
Module that contains the tools required to perform a pipeline computation.
The main object is Computation, which takes a runner and subject and 
runs them against each other
"""
import os
import time
import subprocess
import threading
import shutil
import json
from contextlib import contextmanager

import util
import kimunits
import kimquery
import kimobjects

import config as cf
from logger import logging
logger = logging.getLogger("pipeline").getChild("compute")

#================================================================
# a class to be able to timeout on a command
#================================================================
class Command(object):
    def __init__(self, cmd, stdin=None, stdout=None, stderr=None):
        """
        A class to provide time limits to sub processes. Accepts
        a command as an array (similar to check_output) and file
        handles with which to communicate on stdin, stdout, stderr
        """
        self.cmd = cmd
        self.process = None
        self.stdin = stdin
        self.stdout = stdout
        self.stderr = stderr

    def run(self, timeout):
        """
        Run the command, cutting it off abruptly at timeout,
        where timeout is given in seconds.
        """

        def target():
            self.process = subprocess.Popen(self.cmd, stdin=self.stdin,
                    stdout=self.stdout, stderr=self.stderr, shell=True)
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
    def __init__(self, runner=None, subject=None, result_code="", verify=True):
        """
        A pipeline computation object that utilizes all of the pipeline
        machinery to calculate a result (test or verification or otherwise).

        Parameters:
            * runner : A Test or {Test|Model} Verification object
            * subject : A Test or Model depending on the runner
            * result_code : if provided, the result will be moved
                to the appropriate location
            * verify : whether the result should be verified against
                the property definitions held by official repo
        """
        self.runner = runner
        self.subject = subject
        self.runner_temp = runner
        self.runtime = None
        self.result_code = result_code
        self.info_dict = None
        self.verify = verify

        self.result_path = os.path.join(self.runner_temp.result_leader.lower(), self.result_code)
        self.full_result_path = os.path.join(cf.KIM_REPOSITORY_DIR, self.result_path)

    def _create_tempdir(self):
        """ Create a temporary running directory and copy over the test contents """
        tempname = self.runner.kim_code_name+"_running"+self.result_code+"__"+self.runner.kim_code_id
        self.runner_temp = kimobjects.kim_obj(self.runner.kim_code, search=False, subdir=tempname)
        shutil.copytree(self.runner.path, self.runner_temp.path)

    def _create_output_dir(self):
        """ Make sure that the ``output`` directory exists for results """
        outputdir = os.path.join(self.runner_temp.path,cf.OUTPUT_DIR)
        if not os.path.exists(outputdir):
            os.makedirs(outputdir)

    def _clean_old_run(self):
        """ Delete old temporary files if they exist """
        for flname in cf.INTERMEDIATE_FILES:
            try:
                os.remove(flname)
            except OSError as e:
                pass

    def _delete_tempdir(self):
        shutil.rmtree(self.runner_temp.path)

    @contextmanager
    def tempdir(self):
        """
        Create a temporary directory and copy all objects over so that
        they can run independently of other processes on a single machine.

        A context manager so that you can say:

            with self.tempdir():
                ... do something ...
        """
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
        """
        Execute the runner with the subject as set in the object.  Do this in
        the current directory, wherever that may be.  In the process, also
        collect runtime information using /usr/bin/time profilling
        """
        logger.info("running %r with %r",self.runner,self.subject)

        executable = self.runner_temp.executable
        libc_redirect = "LIBC_FATAL_STDERR_=1 "
        timeblock = "/usr/bin/time --format={\\\"usertime\\\":%U,\\\"memmax\\\":%M,\\\"memavg\\\":%K} "

        # run the runner in its own directory
        with self.runner_temp.in_dir():
            with self.runner_temp.processed_infile(self.subject) as kim_stdin_file,  \
                    open(cf.STDOUT_FILE,'w') as stdout_file, \
                    open(cf.STDERR_FILE,'w') as stderr_file:
                start_time = time.time()

                logger.info("launching run...")
                process = Command(libc_redirect+timeblock+executable,stdin=kim_stdin_file,
                        stdout=stdout_file,stderr=stderr_file)

                try:
                    self.retcode = process.run(timeout=cf.RUNNER_TIMEOUT)
                except PipelineTimeout:
                    logger.error("runner %r timed out",self.runner)
                    raise PipelineTimeout, "your executable timed out at %r hours" % (cf.RUNNER_TIMEOUT / 3600)

                end_time = time.time()

        # It seems the runner didn't finish
        if process.poll() is None:
            process.kill()
            raise cf.KIMRuntimeError, "Your test did not respond to timeout request and did not exit"

        self.runtime = end_time - start_time
        logger.info("Run completed in %r seconds" % self.runtime)
        if self.retcode != 0:
            logger.error("Runner returned error code %r, %r" % (self.retcode, os.strerror(self.retcode)) )
            raise cf.KIMRuntimeError("Executable %r returned error code %r" % (self.runner_temp, self.retcode))

    def process_output(self):
        """
        In the current directory, make sure that the results are ready to
        go by checking that ``RESULT_FILE`` exists and conforms to the
        property definitions that it promises.  Also append SI units
        """
        # Short-circuit if we already have a results.edn
        with self.runner_temp.in_dir():
            if not os.path.isfile(cf.RESULT_FILE):
                raise cf.KIMRuntimeError, "The test did not produce a %s output file." % cf.RESULT_FILE

        # now, let's check whether that was actual a valid test result
        logger.debug("Checking the output EDN for validity")
        with self.runner_temp.in_dir(), open(cf.RESULT_FILE, 'r') as f:
            try:
                doc = util.loadedn(f)
                doc = kimunits.add_si_units(doc)
            except Exception as e:
                raise cf.KIMRuntimeError, "Test did not produce valid EDN %s" % cf.RESULT_FILE

            if self.verify:
                valid, reply = test_result_valid(cf.RESULT_FILE)
                if not valid:
                    raise cf.KIMRuntimeError, "Test result did not conform to property definition\n%r" % reply

        logger.debug("Adding units to result file")
        with self.runner_temp.in_dir(), open(cf.RESULT_FILE, 'w') as f:
            util.dumpedn(doc, f)

        logger.debug("Made it through EDN read, everything looks good")


    def gather_profiling_info(self, extrainfo=None):
        """
        Append the profiling information obtained in ``execute_in_place``
        to the information metadata.  This will saved during the ``write_result``
        method later on.
        """
        # Add metadata
        info_dict = {}
        info_dict["time"] = self.runtime
        info_dict["created-at"] = time.time()
        if extrainfo:
            info_dict.update(extrainfo)

        # get the information from the timing script
        with self.runner_temp.in_dir():
            if os.path.exists(cf.STDERR_FILE):
                with open(cf.STDERR_FILE) as stderr_file:
                    stderr = stderr_file.read()
                time_str = stderr.splitlines()[-1]
                time_dat = json.loads(time_str)
                info_dict.update(time_dat)

        logger.debug("Caching profile information")
        self.info_dict = info_dict


    def write_result(self, error=False):
        """
        Write the remaining information to make the final test result
        object.  This includes:

            * check for errors in the previous steps.  if there are any skip
              and move directory to the error directory

            * Creating ``CONFIG_FILE`` and ``PIPELINESPEC_FILE`` for result
              metadata

            * Moving the ``output`` directory to its final resting place
        """
        if error:
            self.result_path = os.path.join("er", self.result_code)
            self.full_result_path = os.path.join(cf.KIM_REPOSITORY_DIR, self.result_path)

        logger.debug("Copying kim.log")
        with self.runner_temp.in_dir():
            if os.path.exists("./kim.log"):
                shutil.copy2("./kim.log", cf.KIMLOG_FILE)

        # create the kimspec.edn file for the test results
        logger.debug("Create %s file" % cf.CONFIG_FILE)
        kimspec = {}
        kimspec[self.runner.runner_name] = self.runner.kim_code
        kimspec[self.subject.subject_name] = self.subject.kim_code
        kimspec['domain'] = 'openkim.org'

        pipelinespec = {}
        if self.info_dict:
            pipelinespec['profiling'] = self.info_dict
        if self.result_code:
            pipelinespec['UUID'] = self.result_code

        with self.runner_temp.in_dir(), open(os.path.join(cf.OUTPUT_DIR,cf.CONFIG_FILE),'w') as f:
            util.dumpedn(kimspec, f)
        with self.runner_temp.in_dir(), open(os.path.join(cf.OUTPUT_DIR,cf.PIPELINESPEC_FILE),'w') as f:
            util.dumpedn(pipelinespec, f)

        logger.debug("Result path = %s", self.full_result_path)
        outputdir = os.path.join(self.runner_temp.path,cf.OUTPUT_DIR)

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
        Run a runner with the corresponding subject, with /usr/bin/time
        profilling, capture the output as a dict, and return or run a V{T,M}
        with the corresponding {TE,MO}

        If result_code is set, then run in a temporary directory, otherwise
        run in place in the test folder.

        If errors occur, print the last lines of all output files and
        report the error back while moving the result into the errors
        directory.
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

                files = [cf.STDOUT_FILE, cf.STDERR_FILE, cf.KIMLOG_FILE]
                tails = last_output_lines(self.runner_temp, files)

                outs = trace+"\n"
                for f, t in zip(files, tails):
                    outs += f+":\n"
                    outs += "".join(["-"]*(len(f)+1))+"\n"
                    outs += append_newline(t)+"\n"
                raise cf.PipelineRuntimeError(e, outs)

#================================================================
# helper functions
#================================================================
def tail(f, n=5):
    """
    Return the last ``n`` lines of a file ``f`` using
    the unix tool tail and popen.  ``f`` is a str object
    """
    try:
        stdin,stdout = os.popen2("tail -n "+str(n)+" "+f)
        stdin.close()
        lines = stdout.readlines();
        stdout.close()
    except Exception as e:
        lines = [""]
    return "".join(lines)

def last_output_lines(kimobj, files, n=20):
    """ Return the last lines of all output files """
    with kimobj.in_dir():
        tails = [ tail(f, n) for f in files ]
    return tails

def append_newline(string):
    """ Append a newline is there isn't one present """
    if len(string) > 0 and string[-1] != '\n':
        string += "\n"
    return string

def test_result_valid(flname):
    """
    Queries pipeline.openkim.org to figure out if the given
    flname is a valid property based on the property definitions
    available in the official repository:

        https://github.com/openkim/openkim-properties
    """
    reply = json.loads(kimquery.query_property_validator(flname))
    valid = all([ rep['valid'] for rep in reply ])
    return (valid, reply)

