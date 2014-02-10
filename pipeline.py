#! /usr/bin/env python
"""
Pipeline.py is the section of the pipeline that handles the network
communication between directors, workers, and webiste through
the beanstalk daemon.  It is also the main entrance point of the
pipeline worker or director.

It can be called using::

    python pipeline.py director
    python pipeline.py worker

in order to start it up.

Any of the classes below rely on a secure public key to open an ssh
tunnel to the remote host.  It then connects to the beanstalkd
across this tunnel.
"""
from subprocess import check_call, CalledProcessError, Popen, PIPE
from multiprocessing import cpu_count, Process, Lock
from multiprocessing.managers import BaseManager
from contextlib import contextmanager
import sys
import time
import simplejson
import uuid

from config import *
import network
import rsync_tools
import compute
import database
import kimobjects
import kimapi

from logger import logging
logger = logging.getLogger("pipeline").getChild("pipeline")

def getboxinfo():
    """ 
    we need to gather information from two sources, the /pipeline/environment
    file and various of resources, so we split into things and temps or 
    /pipeline/environment and various bash calls
    """
    import urllib
    import re
    things = ['pipeline_sitename', 'pipeline_username', 'boxtype',
            'vmversion', 'setupargs', 'gitbranch', 'githost', 'gitname', 'uuid']

    info = {}
    for thing in things:
        try:
            info[thing] = CONF[thing.upper()]
        except Exception as e:
            info[thing] = None

    info['cpucount'] = cpu_count()
    info['setuphash'] = Popen("cd "+CONF["PIPELINEDIR"]+"; git log -n 1 | grep commit | sed s/commit\ //", 
        stdout=PIPE, shell=True).communicate()[0]

    try:
        info['ipaddr'] = urllib.urlopen("http://pipeline.openkim.org/ip").read()
    except IOError as e:
        logger.error("pipeline.openkim.org could not be reached for ip")
        info['ipaddr'] = None

    try:
        with open(CONF["FILE_BENCHMARK"]) as f:
            content = f.read()
            lps = re.search(r"([0-9\.]+\slps)", content)
            MWIPS = re.search(r"([0-9\.]+\sMWIPS)", content)

            info['benchmark_dry'] = lps.groups()[0] if lps else None
            info['benchmark_whet'] = MWIPS.groups()[0] if MWIPS else None
    except Exception as e:
        logger.error("Benchmark has not been completed")
        info['benchmark_dry'] = info['benchmark_whet'] = None

    try:
        with open("/proc/cpuinfo") as f:
            model = re.search(r"(model name)\s:\s(.*)\n", f.read())
            info['cpu'] = model.groups()[1] if model else None

        with open("/proc/meminfo") as f:
            mem = re.search(r"(MemTotal:)\s*(.*)\n", f.read())
            info['mem'] = mem.groups()[1] if mem else None
    except:
        logger.error("CPU and RAM info could not be found")
        info['cpu'] = info['mem'] = None

    return info

def ll(iterator):
    return len(list(iterator))

def pingpongHandler(header, message, agent):
    if header == "ping":
        agent.comm.send_msg("reply", [agent.uuid, agent.data])

class BuilderBot(object):
    def __init__(self):
        self.mod_buildlocks = Lock()
        self.buildlocks = {}

    def lock_build(self, kimobj):
        with self.mod_buildlocks:
            if not self.buildlocks.get(kimobj.kim_code, None):
                self.buildlocks[kimobj.kim_code] = Lock()
            with self.buildlocks[kimobj.kim_code]:
                try:
                    kimobj.make()
                except Exception as e:
                    raise RuntimeError("Could not make %s" % kimobj.kim_code)

class BuilderManager(BaseManager):
    pass

BuilderManager.register('BuilderBot', BuilderBot, exposed = ['lock_build'])

#==================================================================
# Agent is the base class for Director, Worker, Site
# handles basic networking and message responding (so it is not duplicated)
#==================================================================
class Agent(object):
    def __init__(self, name='worker', num=0, builder=None, rsynclock=None):
        self.boxinfo  = getboxinfo()

        self.builder = builder
        self.rsynclock = rsynclock

        self.job = None
        self.name = name
        self.num = num
        self.uuid = self.boxinfo['uuid']+":"+str(self.num)
        self.logger = logger.getChild("%s-%i" % (self.name, num))
        self.data = {"job": self.job, "data": self.boxinfo}
        self.boxinfo['cid'] = self.num

    def connect(self):
        # start up the 2-way comm too
        self.comm = network.Communicator()
        self.bean = network.BeanstalkConnection()

        self.logger.info("Bringing up RX/TX")
        self.comm.connect()
        self.comm.addHandler(func=pingpongHandler, args=(self,))
        self.comm.start()

        #attach the beanstalk logger
        network.addNetworkHandler(self.comm, self.boxinfo)

        self.logger.info("Connecting to beanstalkd")
        self.bean.connect()
        self.logger.info("%s ready" % self.name.title())

    def disconnect(self):
        self.bean.disconnect()

    def exit_safe(self):
        # we got the signal to shutdown, so release the job first
        if hasattr(self, 'job') and self.job is not None:
            self.job.delete()
            if hasattr(self, 'jobmsg') and self.jobmsg is not None:
                self.job_message(self.jobmsg, errors="Caught SIGINT and killed", tube=TUBE_ERRORS)
        self.disconnect()

    def job_message(self, jobmsg, errors=None, tube=TUBE_RESULTS):
        """ Send back a job message """
        jobmsg.results = None
        jobmsg.errors = "%s" % errors
        jobmsg.update(self.boxinfo)

        if len(jobmsg.errors) > PIPELINE_MSGSIZE:
            jobmsg.errors = "too long"

        msg = simplejson.dumps(jobmsg)
        self.bean.send_msg(tube, msg)
        self.comm.send_msg(tube, msg)

    def make_object(self, kimid):
        self.logger.debug("Building the source for %r", kimid)
        kimobj = kimobjects.KIMObject(kimid)
        with kimobj.in_dir():
            try:
                check_call("make")
            except CalledProcessError as e:
                return 1
            return 0

    @contextmanager
    def in_api_dir(self):
        cwd = os.getcwd()
        os.chdir(KIM_API_DIR)
        try:
            yield
        except Exception as e:
            raise e
        finally:
            os.chdir(cwd)

    def make_all(self):
        self.logger.debug("Building everything...")
        with self.in_api_dir():
            try:
                with open(os.path.join(KIM_LOG_DIR, "make.log"), "a") as log:
                    check_call(["make", "clean"], shell=True, stdout=log, stderr=log)
                with open(os.path.join(KIM_LOG_DIR, "make.log"), "a") as log:
                    check_call(["make"], shell=True, stdout=log, stderr=log)
            except CalledProcessError as e:
                self.logger.error("could not make kim")
                raise RuntimeError, "Could not build entire repository"
            return 0

    def make_api(self):
        self.logger.debug("Building the API...")
        with self.in_api_dir():
            try:
                with open(os.path.join(KIM_LOG_DIR, "make.log"), "a") as log:
                    check_call(["make", "clean"], shell=True, stdout=log, stderr=log)
                with open(os.path.join(KIM_LOG_DIR, "make.log"), "a") as log:
                    check_call(["make"], shell=True, stdout=log, stderr=log)
            except CalledProcessError as e:
                self.logger.error("Could not make KIM API")
                raise RuntimeError, "Could not make KIM API"
            return 0


#==================================================================
# director class for the pipeline
#==================================================================
class Director(Agent):
    """ The Director object, knows to listen to incoming jobs, computes dependencies
    and passes them along to workers
    """
    def __init__(self, num=0, *args, **kwargs):
        super(Director, self).__init__(name="director", num=num, *args, **kwargs)

    def run(self):
        """
        Endless loop that waits for updates on the tube TUBE_UPDATES

        The update is a json string for a dictionary with key-values pairs
        that look like:

            * kimid : any form of the kimid that is recognized by the database package
            * priority : one of 'immediate', 'very high', 'high', 'normal', 'low', 'very low'
            * status : one of 'approved', 'pending' where pending signifies it has just been
                submitted and needs to go through VCs whereas approved is to initiate a full match
                run after verification or update

        """
        # connect and grab the job thread
        self.connect()
        self.bean.watch(TUBE_UPDATES)

        while True:
            self.logger.info("Director Waiting for message...")
            request = self.bean.reserve()
            self.job = request

            # make sure it doesn't come alive again soon
            request.bury()

            # got a request to update a model or test
            # from the website (or other trusted place)
            if request.stats()['tube'] == TUBE_UPDATES:
                # update the repository,send it out as a job to compute
                try:
                    rsync_tools.director_approved_read()
                    self.push_jobs(simplejson.loads(request.body))
                except Exception as e:
                    self.logger.exception("Director had an error on update")

            request.delete()
            self.job = None

    def priority_to_number(self,priority):
        priorities = {"immediate": 0, "very high": 0.01, "high": 0.1,
                      "normal": 1, "low": 10, "very low": 100}
        if priority not in priorities.keys():
            priority = "normal"
        return priorities[priority]

    def push_jobs(self, update):
        """ Push all of the jobs that need to be done given an update """
        kimid = update['kimid']
        status = update['status']
        priority_factor = self.priority_to_number(update['priority'])

        name,leader,num,version = database.parse_kim_code(kimid)

        self.make_all()

        checkmatch = False
        if leader=="VT":
            # for every test launch
            test = kimobjects.VerificationTest(kimid)
            models = list(kimobjects.Test.all())
            tests = [test]*ll(models)
        elif leader=="VM":
            #for all of the models, run a job
            test = kimobjects.VerificationModel(kimid)
            models = list(kimobjects.Model.all())
            tests = [test]*ll(models)
        else:
            if status == "approved":
                if leader=="TE":
                    # for all of the models, add a job
                    test = kimobjects.Test(kimid)
                    models = list(test.models)
                    tests = [test]*ll(models)
                elif leader=="MO":
                    # for all of the tests, add a job
                    model = kimobjects.Model(kimid)
                    tests = list(model.tests)
                    models = [model]*ll(tests)
                elif leader=="TD":
                    # if it is a new version of an existing test driver, hunt
                    # down all of the tests that use it and launch their
                    # corresponding jobs
                    driver = kimobjects.TestDriver(kimid)
                    temp_tests = list(driver.tests)
                    models = []
                    tests = []
                    for t in temp_tests:
                        tmodels = list(t.models)
                        if len(tmodels) > 0:
                            models.extend(tmodels)
                            tests.extend([t]*ll(tmodels))

                elif leader=="MD":
                    # if this is a new version, hunt down all of the models
                    # that rely on it and recompute their results
                    driver = kimobjects.ModelDriver(kimid)
                    temp_models = list(driver.models)
                    tests = []
                    models = []
                    for m in temp_models:
                        mtests = list(m.tests)
                        if len(mtests) > 0:
                            tests.extend(mtests)
                            models.extend([m]*ll(mtests))
                else:
                    self.logger.error("Tried to update an invalid KIM ID!: %r",kimid)
                checkmatch = True
            if status == "pending":
                rsync_tools.director_pending_read(kimid)
                self.make_all()

                if leader=="TE":
                    # run against all test verifications
                    tests = list(kimobjects.VertificationTest.all())
                    models = [kimobjects.Test(kimid, search=False)]*ll(tests)
                elif leader=="MO":
                    # run against all model verifications
                    tests = list(kimobjects.VertificationModel.all())
                    models = [kimobjects.Model(kimid, search=False)]*ll(tests)
                elif leader=="TD":
                    # a pending test driver
                    pass
                elif leader=="MD":
                    # a pending model driver
                    pass
                else:
                    self.logger.error("Tried to update an invalid KIM ID!: %r",kimid)
                checkmatch = False

        if checkmatch:
            for test, model in zip(tests,models):
                if kimapi.valid_match(test,model):
                    priority = int(priority_factor*database.test_model_to_priority(test,model) * 1000000)
                    self.check_dependencies_and_push(test,model,priority,status)
        else:
            for test, model in zip(tests,models):
                priority = int(priority_factor*database.test_model_to_priority(test,model) * 1000000)
                self.check_dependencies_and_push(test,model,priority,status)


    def check_dependencies_and_push(self, test, model, priority, status, child=None):
        """ Check dependencies, and push them first if necessary """
        # run the test in its own directory
        depids = (str(item) for item in test.dependencies + model.dependencies)
        with test.in_dir():
            trid = self.get_result_code()
            self.logger.info("Submitting job <%s, %s, %s> priority %i" % (test, model, trid, priority))

            msg = network.Message(job=(str(test),str(model)),jobid=trid,
                    child=child, depends=tuple(depids), status=status)
            self.job_message(msg, tube=TUBE_JOBS)

        return depids

    def get_result_code(self):
        return str(uuid.uuid1( uuid.UUID(self.boxinfo['uuid']).int >> 80 ))


#==================================================================
# worker class for the pipeline
#==================================================================
class Worker(Agent):
    """ Represents a worker, knows how to do jobs he is given, create results and rsync them back """
    def __init__(self, num=0, *args, **kwargs):
        super(Worker, self).__init__(name='worker', num=num, *args, **kwargs)

    def run(self):
        """ Start to listen, tunnels should be open and ready """
        self.connect()
        self.bean.watch(TUBE_JOBS)

        """ Endless loop that awaits jobs to run """
        while True:
            self.logger.info("Waiting for jobs...")
            job = self.bean.reserve()
            self.job = job

            # if appears that there is a 120sec re-birth of jobs that have been reserved
            # and I do not want to put an artificial time limit, so let's bury jobs
            # when we get them
            job.bury()
            self.comm.send_msg("running", job.body)

            # update the repository, attempt to run the job and return the results to the director
            try:
                jobmsg = network.Message(string=job.body)
                pending = True if jobmsg == "pending" else False
            except simplejson.JSONDecodeError:
                # message is not JSON decodeable
                self.logger.error("Did not recieve valid JSON, {}".format(job.body))
                job.delete()
                continue
            except KeyError:
                # message does not have the right keys
                self.logger.error("Did not recieve a valid message, missing key: {}".format(job.body))
                job.delete()
                continue

            self.jobmsg = jobmsg
            try:
                name,leader,num,version = database.parse_kim_code(jobmsg.job[0])
            except InvalidKIMID as e:
                # we were not given a valid kimid
                self.logger.error("Could not parse {} as a valid KIMID".format(jobmsg.job[0]))
                self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                job.delete()
                continue

            try:
                # check to see if this is a verifier or an actual test
                with self.rsynclock:
                    self.logger.info("Rsyncing from repo %r", jobmsg.job+jobmsg.depends)
                    rsync_tools.worker_read(*jobmsg.job, depends=jobmsg.depends, pending=pending)

                runner_kcode, subject_kcode = jobmsg.job
                runner  = kimobjects.kim_obj(runner_kcode)
                subject = kimobjects.kim_obj(subject_kcode)

                for driver in runner.drivers:
                    self.builder.lock_build(driver)
                self.builder.lock_build(runner)

                for driver in subject.drivers:
                    self.builder.lock_build(driver)
                self.builder.lock_build(subject)

                self.logger.info("Running (%r,%r)", runner, subject)
                comp = compute.Computation(runner, subject, result_code=jobmsg.jobid)

                errormsg = None
                try:
                    comp.run(extrainfo=self.boxinfo)
                except Exception as e:
                    errormsg = e
                    self.logger.exception("Errors occured, moving to er/")
                else:
                    self.logger.debug("Sending result message back")
                finally:
                    self.logger.info("Rsyncing results %r", jobmsg.jobid)
                    with self.rsynclock:
                        rsync_tools.worker_write(comp.result_path)
                    if errormsg:
                        self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                    else:
                        self.job_message(jobmsg, tube=TUBE_RESULTS)

                job.delete()

            except Exception as e:
                self.logger.exception("Failed to initalize run, deleting... %r" % e)
                self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                job.delete()

            self.job = None
            self.jobsmsg = None

#=========================================================
# emulator for the website so we can do independent debug
#=========================================================
class Site(Agent):
    """ False stand in for the website, pushes TR ids for us and can update models or tests """
    def __init__(self, num=0):
        super(Site, self).__init__(name='website')

    def run(self):
        self.connect()

    def send_update(self, kimid):
        self.logger.info("Pushing jobs")
        self.bean.send_msg("web_updates", simplejson.dumps({"kimid": kimid, "priority":"normal", "status":"approved"}))


class APIAgent(Agent):
    def __init__(self, num=0):
        super(APIAgent, self).__init__(name='api')

    def run(self):
        self.connect()
        while True:
            time.sleep(1)

#=======================================================
# MAIN
#=======================================================
pipe = {}
procs = {}
def signal_handler(): #signal, frame):
    logger.info("Sending signal to flush, wait 1 sec...")
    for p in pipe.values():
        p.exit_safe()
    for p in procs.values():
        p.join(timeout=1)
    sys.exit(1)

if __name__ == "__main__":
    import sys
    if PIPELINE_REMOTE:
        logger.info("REMOTE MODE: ON")

    if PIPELINE_DEBUG:
        logger.info("DEBUG MODE: ON")

    if PIPELINE_GATEWAY:
        logger.info("GATEWAY MODE: ON")

    network.open_ports(BEAN_PORT, PORT_RX, PORT_TX, GLOBAL_USER, GLOBAL_HOST, GLOBAL_IP)

    manager = BuilderManager()
    manager.start()
    builder = manager.BuilderBot()
    rsynclock = Lock()

    if len(sys.argv) > 1:
        # directors are not multithreaded for build safety
        if sys.argv[1] == "director":
            director = Director(num=0)
            logger.info("Building KIM API...")
            director.make_api()
            director.run()

        # workers can be multi-threaded so launch the appropriate
        # number of worker threads
        elif sys.argv[1] == "worker":
            thrds = cpu_count()
            for i in range(thrds):
                pipe[i] = Worker(num=i, builder=builder, rsynclock=rsynclock)

                if i == 0:
                    logger.info("Building KIM API as worker 0")
                    pipe[i].make_api()

                procs[i] = Process(target=Worker.run, args=(pipe[i],), name='worker-%i'%i)
                #procs[i].daemon = True
                procs[i].start()

            try:
                while True:
                    for i in range(thrds):
                        procs[i].join(timeout=1.0)
            except (KeyboardInterrupt, SystemExit):
                signal_handler()

        # site is a one off for testing
        elif sys.argv[1] == "site":
            obj = Site()
            obj.run()
            obj.send_update(sys.argv[2])

        elif sys.argv[1] == "agent":
            obj = APIAgent()
            obj.run()

    else:
        logger.info("Specify {worker|director|site}")
