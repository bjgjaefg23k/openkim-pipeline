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
from multiprocessing import cpu_count, Process, Lock, Queue
# from threading import Thread, Lock
import sys
import time
import simplejson
import traceback

from config import *
import network
import rsync_tools
import compute
import database
import kimobjects
import kimapi

from logger import logging
logger = logging.getLogger("pipeline").getChild("pipeline")

PIPELINE_WAIT    = 1
PIPELINE_TIMEOUT = 60
PIPELINE_MSGSIZE = 2**20
PIPELINE_JOB_TIMEOUT = 3600*24
buildlock = Lock()
loglock = Lock()

def getboxinfo():
    os.system("cd /home/vagrant/openkim-pipeline; git log -n 1 | grep commit | sed s/commit\ // > /persistent/setuphash")

    info = {}
    things = ['sitename', 'username', 'boxtype',
            'ipaddr', 'vmversion', 'setuphash', 'uuid',
            'gitargs', 'gitbranch', 'githost']

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
class Agent(Process):
    def __init__(self, name='worker', num=0):
        super(Agent,self).__init__(None,name=name)

        self.boxinfo  = getboxinfo()
        self.job = None
        self.name = name
        self.num = num
        self.uuid = self.boxinfo['uuid']+":"+str(self.num)

        # self.comm   = network.Communicator()
        # self.bean   = network.BeanstalkConnection()
        self.logger = logger.getChild("%s-%i" % (self.name, num))

        self.data = {"job": self.job, "data": self.boxinfo}

    def connect(self):
        # start up the 2-way comm too
        with loglock:
            self.logger.info("Bringing up RX/TX")
        self.comm   = network.Communicator()
        self.bean   = network.BeanstalkConnection()
        self.comm.connect()
        self.comm.addHandler(func=pingpongHandler, args=(self,))
        self.comm.start()

        #attach the beanstalk logger
        network.addNetworkHandler(self.comm, self.boxinfo)

        with loglock:
            self.logger.info("Connecting to beanstalkd")
        self.bean.connect()
        with loglock:
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

    def job_message(self, jobmsg, errors=None, results=None, tube=TUBE_RESULTS):
        """ Send back a job message """
        jobmsg.results = results
        jobmsg.errors = errors
        jobmsg.update(self.boxinfo)
        msg = simplejson.dumps(jobmsg)

        self.bean.send_msg(tube, msg)
        self.comm.send_msg(tube, msg)

    def make_object(self, kimid):
        with loglock:
            self.logger.debug("Building the source for %r", kimid)
        kimobj = kimobjects.KIMObject(kimid)
        with kimobj.in_dir():
            try:
                check_call("make")
            except CalledProcessError as e:
                return 1
            return 0

    def make_all(self):
        with loglock:
            self.logger.debug("Building everything...")
        try:
            check_call("makekim",shell=True)
        except CalledProcessError as e:
            with loglock:
                self.logger.error("could not makekim")
            self.job_message(job, errors="could not makekim!", tube=TUBE_ERRORS)

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
        """ connect and grab the job thread """
        self.connect()
        self.bean.watch(TUBE_UPDATES)
        self.run_job()

    def run_job(self):
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
                    rsync_tools.director_full_approved_read()
                    self.push_jobs(simplejson.loads(request.body))
                except Exception as e:
                    tb = traceback.format_exc()
                    self.logger.error("Director had an error on update: {}\n {}".format(e, tb))

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

        # try to build the kimid before sending jobs
        # if self.make_object(kimid) == 0:
        #     rsync_tools.director_build_write(kimid)
        # else:
        #     self.logger.error("Could not build %r", kimid)
        #     self.bsd.use(TUBE_ERRORS)
        #     self.bsd.put(simplejson.dumps({"error": "Could not build %r" % kimid}))
        #     return

        self.make_all()

        if leader=="VT":
            # for every test launch
            test = kimobjects.VerificationTest(kimid)
            models = kimobjects.Test.all()
            tests = [test]*ll(models)
        elif leader=="VM":
            #for all of the models, run a job
            test = kimobjects.VerificationModel(kimid)
            models = kimobjects.Model.all()
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
                if leader=="TE":
                    # a pending test
                    rsync_tools.director_test_verification_read(kimid)
                    self.make_all()

                    # run against all test verifications
                    tests = list(kimobjects.VertificationTest.all())
                    models = [kimobjects.Test(kimid, search=False)]*ll(tests)
                elif leader=="MO":
                    # a pending model
                    rsync_tools.director_model_verification_read(kimid)
                    self.make_all()

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

            if test.kim_code_leader == "VT" or test.kim_code_leader == "VM":
                trid = self.get_vr_id()
            else:
                trid = self.get_tr_id()
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

    def get_tr_id(self):
        return kimobjects.new_test_result_id()

    def get_vr_id(self):
        return kimobjects.new_verification_result_id()


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
        self.run_job()


    def run_job(self):
        """ Endless loop that awaits jobs to run """
        while True:
            with loglock:
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
            except simplejson.JSONDecodeError:
                # message is not JSON decodeable
                with loglock:
                    self.logger.error("Did not recieve valid JSON, {}".format(job.body))
                job.delete()
                continue
            except KeyError:
                # message does not have the right keys
                with loglock:
                    self.logger.error("Did not recieve a valid message, missing key: {}".format(job.body))
                job.delete()
                continue

            self.jobmsg = jobmsg
            # check to see if this is a verifier or an actual test
            try:
                name,leader,num,version = database.parse_kim_code(jobmsg.job[0])
            except InvalidKIMID as e:
                # we were not given a valid kimid
                with loglock:
                    self.logger.error("Could not parse {} as a valid KIMID".format(jobmsg.job[0]))
                self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                job.delete()
                continue

            if leader == "VT" or leader == "VM":
                try:
                    with buildlock:
                        with loglock:
                            self.logger.info("rsyncing to repo %r", jobmsg.job+jobmsg.depends)
                        rsync_tools.worker_verification_read(*jobmsg.job, depends=jobmsg.depends)
                        self.make_all()

                    verifier_kcode, subject_kcode = jobmsg.job
                    verifier = kimobjects.Verifier(verifier_kcode)
                    subject  = kimobjects.Subject(subject_kcode)

                    with loglock:
                        self.logger.info("Running (%r,%r)",verifier,subject)
                    comp = compute.Computation(verifier, subject)
                    comp.run(jobmsg.jobid)

                    result = kimobjects.Result(jobmsg.jobid).results
                    with loglock:
                        self.logger.info("rsyncing results %r", jobmsg.jobid)
                    rsync_tools.worker_verification_write(jobmsg.jobid)
                    with loglock:
                        self.logger.info("sending result message back")
                    self.job_message(jobmsg, results=result, tube=TUBE_RESULTS)
                    job.delete()

                # could be that a dependency has not been met.
                # put it back on the queue to wait
                except PipelineDataMissing as e:
                    if job.stats()['age'] < 5*PIPELINE_JOB_TIMEOUT:
                        with loglock:
                            self.logger.error("Run failed, missing data.  Returning to queue... (%r)" % e)
                        job.release(delay=PIPELINE_JOB_TIMEOUT)
                    else:
                        with loglock:
                            self.logger.error("Run failed, missing data. Lifetime has expired, deleting (%r)" % e)
                        job.delete()

                # another problem has occurred.  just remove the job
                # and send the error back along the error queue
                except Exception as e:
                    with loglock:
                        self.logger.error("Run failed, deleting... %r" % e)
                    self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                    job.delete()
            else:
                try:
                    with buildlock:
                        with loglock:
                            self.logger.info("rsyncing to repo %r %r", jobmsg.job,jobmsg.depends)
                        rsync_tools.worker_test_result_read(*jobmsg.job, depends=jobmsg.depends)
                        self.make_all()

                    test_kcode, model_kcode = jobmsg.job
                    test = kimobjects.Test(test_kcode)
                    model = kimobjects.Model(model_kcode)

                    with loglock:
                        self.logger.info("Running (%r,%r)",test,model)
                    comp = compute.Computation(test, model)
                    comp.run(jobmsg.jobid)

                    result = kimobjects.Result(jobmsg.jobid).results
                    with loglock:
                        self.logger.info("rsyncing results %r", jobmsg.jobid)
                    rsync_tools.worker_test_result_write(jobmsg.jobid)
                    with loglock:
                        self.logger.info("sending result message back")
                    self.job_message(jobmsg, results=result, tube=TUBE_RESULTS)
                    job.delete()

                # could be that a dependency has not been met.
                # put it back on the queue to wait
                except PipelineDataMissing as e:
                    if job.stats()['age'] < 5*PIPELINE_JOB_TIMEOUT:
                        with loglock:
                            self.logger.error("Run failed, missing data.  Returning to queue... (%r)" % e)
                        job.release(delay=PIPELINE_JOB_TIMEOUT)
                    else:
                        with loglock:
                            self.logger.error("Run failed, missing data. Lifetime has expired, deleting (%r)" % e)
                        job.delete()

                # another problem has occurred.  just remove the job
                # and send the error back along the error queue
                except Exception as e:
                    with loglock:
                        self.logger.error("Run failed, deleting... %r" % e)
                    self.job_message(jobmsg, errors="%r"%e, tube=TUBE_ERRORS)
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
    print "Sending signal to flush, wait 1 sec..."
    for p in pipe.values():
        p.exit_safe()
    for p in procs.values():
        p.join(timeout=1)
    sys.exit(1)

network.open_ports(BEAN_PORT, PORT_RX, PORT_TX, GLOBAL_USER, GLOBAL_HOST, GLOBAL_IP)


def run_worker(q):
    worker = q.get()
    q.run()

if __name__ == "__main__":
    import sys
    import time
    if PIPELINE_REMOTE:
        print "REMOTE MODE: ON"

    if PIPELINE_DEBUG:
        print "DEBUG MODE: ON"

    if PIPELINE_GATEWAY:
        print "GATEWAY MODE: ON"


    if len(sys.argv) > 1:
        # directors are not multithreaded for build safety
        if sys.argv[1] == "director":
            director = Director(num=0)
            director.run()

        # workers can be multi-threaded so launch the appropriate
        # number of worker threads
        elif sys.argv[1] == "worker":
            thrds = cpu_count()
            print "thrds=", thrds
            thrds = 3
            for i in xrange(thrds):
                pipe[i] = Worker(num=i)
                pipe[i].daemon = True
                pipe[i].start()

            print "after creation"
            # try:
            #     while True:
            #         print "looping.."
            #         for i in xrange(thrds):
            #             pipe[i].join(timeout=1.0)
            # except (KeyboardInterrupt, SystemExit):
            #     signal_handler()
            while True:
                print "wait..."
                time.sleep(1)

        # site is a one off for testing
        elif sys.argv[1] == "site":
            obj = Site()
            obj.run()
            obj.send_update(sys.argv[2])

        elif sys.argv[1] == "agent":
            obj = APIAgent()
            obj.run()

    else:
        print "Specify {worker|director|site}"

    print "Bottom"
