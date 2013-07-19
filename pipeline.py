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
from subprocess import check_call, CalledProcessError
from multiprocessing import cpu_count, Process, Lock
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

buildlock = Lock()

def getboxinfo():
    os.system("cd /home/openkim/openkim-pipeline; git log -n 1 | grep commit | sed s/commit\ // > /persistent/setuphash")

    info = {}
    things = ['pipeline_sitename', 'pipeline_username', 'boxtype',
            'vmversion', 'setupargs', 'gitbranch', 'githost', 'gitname']
    temp = ['ipaddr', 'setuphash', 'uuid', 'benchmark']

    for thing in things:
        try:
            info[thing] = open(os.path.join('/persistent',thing)).read().strip()
        except Exception as e:
            info[thing] = None
    return info

class Message(dict):
    def __init__(self, **kwargs):
        super(Message, self).__init__()
        dic = kwargs
        if kwargs.has_key('string'):
            dic = simplejson.loads(kwargs['string'])
        for key in dic.keys():
            self[key] = dic[key]

    def __getattr__(self, name):
        if not self.has_key(name):
            return None
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __repr__(self):
        return simplejson.dumps(self)

def ll(iterator):
    return len(list(iterator))

def pingpongHandler(header, message, agent):
    if header == "ping":
        agent.comm.send_msg("reply", [agent.uuid, agent.data])

#==================================================================
# Agent is the base class for Director, Worker, Site
# handles basic networking and message responding (so it is not duplicated)
#==================================================================
class Agent(object):
    def __init__(self, name='worker', num=0):
        self.boxinfo  = getboxinfo()

        self.job = None
        self.name = name
        self.num = num
        self.uuid = self.boxinfo['uuid']+":"+str(self.num)
        self.logger = logger.getChild("%s-%i" % (self.name, num))
        self.data = {"job": self.job, "data": self.boxinfo}

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
        jobmsg.errors = "%r" % errors
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

    def make_all(self):
        self.logger.debug("Building everything...")
        try:
            check_call("makekim",shell=True)
        except CalledProcessError as e:
            self.logger.error("could not makekim")

            raise RuntimeError, "our makekim failed!"
            return 1
        return 0

#==================================================================
# director class for the pipeline
#==================================================================
class Director(Agent):
    """ The Director object, knows to listen to incoming jobs, computes dependencies
    and passes them along to workers
    """
    def __init__(self, num=0):
        super(Director, self).__init__(name="director", num=num)

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
        depids = []
        with test.in_dir():
            #grab the input file
            ready, TRs, PAIRs = test.dependency_check(model)
            self.logger.debug("Dependency check returned <%s, %s, %s>" % (ready, TRs, PAIRs))
            TR_ids = tuple(map(str,TRs)) if TRs else ()

            if hasattr(model, "model_driver"):
                md = model.model_driver
                if md:
                    TR_ids += (md.kim_code,)

            trid = self.get_result_code()
            self.logger.info("Submitting job <%s, %s, %s> priority %i" % (test, model, trid, priority))

            if not ready:
                if PAIRs:
                    for (t,m) in PAIRs:
                        self.logger.info("Submitting dependency <%s, %s>" % (t, m))
                        depids.append(self.check_dependencies_and_push(str(t),str(m),priority/10,
                            status,child=(str(test),str(model),trid)))

            msg = Message(job=(str(test),str(model)),jobid=trid,
                    child=child, depends=TR_ids+tuple(depids), status=status)
            self.job_message(msg, tube=TUBE_JOBS)

        return depids

    def get_result_code(self):
        return str(uuid.uuid1( uuid.UUID(self.boxinfo['uuid']).int >> 80 ))


#==================================================================
# worker class for the pipeline
#==================================================================
class Worker(Agent):
    """ Represents a worker, knows how to do jobs he is given, create results and rsync them back """
    def __init__(self, num=0):
        super(Worker, self).__init__(name='worker', num=num)

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
                jobmsg = Message(string=job.body)
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
                with buildlock:
                    self.logger.info("Rsyncing from repo %r", jobmsg.job+jobmsg.depends)
                    rsync_tools.worker_read(*jobmsg.job, depends=jobmsg.depends, pending=pending)
                    self.make_all()

                runner_kcode, subject_kcode = jobmsg.job
                runner  = kimobjects.kim_obj(runner_kcode)
                subject = kimobjects.kim_obj(subject_kcode)

                self.logger.info("Running (%r,%r)", runner, subject)
                comp = compute.Computation(runner, subject, result_code=jobmsg.jobid)

                errormsg = None
                try:
                    comp.run()
                except Exception as e:
                    errormsg = e
                    self.logger.exception("Errors occured, moving to er/")
                else:
                    self.logger.debug("Sending result message back")
                finally:
                    self.logger.info("Rsyncing results %r", jobmsg.jobid)
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

network.open_ports(BEAN_PORT, PORT_RX, PORT_TX, GLOBAL_USER, GLOBAL_HOST, GLOBAL_IP)

if __name__ == "__main__":
    import sys
    if PIPELINE_REMOTE:
        logger.info("REMOTE MODE: ON")

    if PIPELINE_DEBUG:
        logger.info("DEBUG MODE: ON")

    if PIPELINE_GATEWAY:
        logger.info("GATEWAY MODE: ON")


    if len(sys.argv) > 1:
        # directors are not multithreaded for build safety
        if sys.argv[1] == "director":
            director = Director(num=0)
            director.run()

        # workers can be multi-threaded so launch the appropriate
        # number of worker threads
        elif sys.argv[1] == "worker":
            thrds = cpu_count()
            for i in range(thrds):
                pipe[i] = Worker(num=i)
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
