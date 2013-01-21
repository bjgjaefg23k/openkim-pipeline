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
from config import *
import beanstalkc as bean
from subprocess import check_call, Popen, PIPE, CalledProcessError
from multiprocessing import cpu_count, Process
from threading import Thread
import time, simplejson, traceback, sys, zmq, uuid
import rsync_tools, runner, kimapi, database 
import kimobjects

PIPELINE_WAIT    = 1
PIPELINE_TIMEOUT = 60
PIPELINE_MSGSIZE = 2**20
PIPELINE_JOB_TIMEOUT = 3600*24 #one day 

TUBE_UPDATE  = "updates"
TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_ERRORS  = "errors"
TUBE_LOG     = "logs"

BEANSTALK_LEVEL = logging.INFO

def open_ports(port, rx, tx, user, addr, ip):
    try:
        bsd = bean.Connection(GLOBAL_IP, GLOBAL_PORT, PIPELINE_WAIT)
        bsd.close()
    except bean.SocketError:
        st  = ""
        st += "screen -dm ssh -i /persistent/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "  
        st +=                 "-L{}:{}:{}   -L{}:{}:{}  -L{}:{}:{}  {}@{}"
        ssh = Popen(st.format(port,ip,port,  rx,ip,rx,  tx,ip,tx,   user,addr), shell=True)
        logger.info("Waiting to open ports via ssh tunnels")
        time.sleep(PIPELINE_WAIT)

#==================================================================
# communicator which gathers the information and sends out requests
#==================================================================
class Communicator(Thread):
    def __init__(self):
        self.data = {}

        # decide on the port order
        self.port_tx = PORT_TX
        self.port_rx = PORT_RX 
 
        super(Communicator, self).__init__()
        self.daemon = True

    def connect(self):
        self.con = zmq.Context()
        # open both the rx/tx lines, bound
        self.sock_tx = self.con.socket(zmq.PUB)
        self.sock_tx.connect("tcp://127.0.0.1:"+str(self.port_tx))
 
        self.sock_rx = self.con.socket(zmq.SUB)
        self.sock_rx.setsockopt(zmq.SUBSCRIBE, "")
        self.sock_rx.connect("tcp://127.0.0.1:"+str(self.port_rx))

    def disconnect(self):
        pass

    def register(self, **kwargs):
        for key in kwargs.keys():
            self.data[key] = kwargs[key]

    def run(self):
        while 1:
            try:
                obj = self.sock_rx.recv_pyobj()
                header, message = obj

                # then it is a string, test which type it is
                if header == "ping":
                    self.sock_tx.send_pyobj(("ping", simplejson.dumps(["reply", self.data['uuid'], self.data])))

                # we have a four part request, parse it
                if header == "api":
                    uuid, responseid, query = simplejson.loads(message)
                    if uuid == self.data['uuid']:
                        logger.info("Got api request: /%s ..." % query)
                        ret = kimobjects.data.api("/"+query)
                        logger.info("Object found for request /%s" % query)
                        self.sock_tx.send_pyobj( ("api", simplejson.dumps((responseid, ret))) )

            except Exception as e:
                # just let it go, you failed.
                logger.error("comm had an error: %r" % e)
                if header == "api":
                    self.sock_tx.send_pyobj( ("api", simplejson.dumps((responseid, "ERROR: %r" % e))) )
                pass

    def send_msg(self, tube, msg):
        self.sock_tx.send_pyobj([tube, msg])


#==================================================================
# the logging handler for beanstalkd queues
#==================================================================
class BeanstalkHandler(logging.Handler):
    """ A beanstalk logging handler """
    def __init__(self,comm):
        self.comm = comm 
        self.info = runner.getboxinfo()
        super(BeanstalkHandler,self).__init__()

    def emit(self,record):
        """ Send the message """
        err_message = self.format(record)
        message = self.info.copy()
        message['message'] = err_message
        self.comm.send_msg(TUBE_LOG,simplejson.dumps(message))

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


#==================================================================
# Agent is the base class for Director, Worker, Site
# handles basic networking and message responding (so it is not duplicated)
#==================================================================
class Agent(object):
    def __init__(self, name='worker', num=0, uuid=uuid.uuid4()):
        self.ip       = GLOBAL_IP
        self.port     = GLOBAL_PORT
        self.timeout  = PIPELINE_TIMEOUT
        self.msg_size = PIPELINE_MSGSIZE
        self.boxinfo  = runner.getboxinfo()

        self.job = None
        self.name = name
        self.num = num
        self.halt = False
        self.uuid = uuid.hex+":"+str(self.num)

        self.comm   = Communicator()
        self.logger = logger.getChild("%s-%i" % (self.name, num))

    def connect(self):
        # start up the 2-way comm too
        self.comm.connect()
        self.comm.register(uuid=self.uuid, job=self.job, boxinfo=self.boxinfo)
        self.comm.start()

        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except bean.SocketError:
            # We failed to connect, this is really bad
            self.logger.error("Failed to connect to beanstalk queue after launching ssh")
            raise bean.SocketError("Failed to connect to %s" % GLOBAL_HOST)

        #attach the beanstalk logger
        beanstalk_handler = BeanstalkHandler(self.comm)
        beanstalk_handler.setLevel(BEANSTALK_LEVEL)
        beanstalk_handler.setFormatter(log_formatter)
        self.logger.addHandler(beanstalk_handler)
        self.logger.info("%s ready" % self.name.title())

    def disconnect(self):
        if self.bsd:
            self.bsd.close()

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
        self.bsd.use(tube)
        self.bsd.put(msg)
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
    def __init__(self, num=0, uuid=''):
        super(Director, self).__init__(name="director", num=num, uuid=uuid)

    def run(self):
        """ connect and grab the job thread """
        self.connect()
        self.bsd.watch(TUBE_UPDATE)
        self.bsd.ignore("default")
        self.get_updates()

    def get_updates(self):
        """
        Endless loop that waits for updates on the tube TUBE_UPDATE

        The update is a json string for a dictionary with key-values pairs
        that look like:

            * kimid : any form of the kimid that is recognized by the database package
            * priority : one of 'immediate', 'very high', 'high', 'normal', 'low', 'very low'
            * status : one of 'approved', 'pending' where pending signifies it has just been
                submitted and needs to go through VCs whereas approved is to initiate a full match
                run after verification or update

        """
        while not self.halt:
            self.logger.info("Director Waiting for message...")
            request = self.bsd.reserve()
            self.job = request

            # make sure it doesn't come alive again soon
            request.bury()

            # got a request to update a model or test
            # from the website (or other trusted place)
            if request.stats()['tube'] == TUBE_UPDATE:
                # update the repository,send it out as a job to compute
                try:    
                    # FIXME - Alex, there are just so many dependencies, I'm going to read the
                    # whole thing.  The latest was submitting a single test after a complete repo
                    # wipe - it pulled the TRs to get a unique jobid to submit, but the TRs referred
                    # tests which hadn't been pulled causing errors...
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

        if leader=="VT":
            # we have a new VT
            # first pull it and build it
            rsync_tools.director_new_test_verification_read(kimid)
            self.make_all()

            # for every test launch
            test = kimobjects.VerificationTest(kimid)
            models = kimobjects.Test.all()
            tests = [test]*ll(models)
        elif leader=="VM":
            # we have a new VM

            # first pull it and build it
            rsync_tools.director_new_model_verification_read(kimid)
            self.make_all()

            #for all of the models, run a job
            test = kimobjects.VerificationModel(kimid)
            models = kimobjects.Model.all()
            tests = [test]*ll(models)
        else:
            if status == "approved":
                if leader=="TE":
                    # we have a new TE, first pull it and build it
                    rsync_tools.director_new_test_read(kimid)
                    self.make_all()

                    # for all of the models, add a job
                    test = kimobjects.Test(kimid)
                    models = list(test.models)
                    tests = [test]*ll(models)
                elif leader=="MO":
                    # we have a model, first pull it and build it
                    rsync_tools.director_new_model_read(kimid)
                    self.make_all()

                    # for all of the tests, add a job
                    model = kimobjects.Model(kimid)
                    tests = list(model.tests)
                    models = [model]*ll(tests)
                elif leader=="TD":
                    # we have a new test driver, first pull and build it
                    rsync_tools.director_new_test_driver_read(kimid)
                    self.make_all()

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
                    # we have a new model driver, first build and push
                    rsync_tools.director_new_model_driver_read(kimid)
                    self.make_all()

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

        if checkmatch == True:
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
        return database.new_test_result_id()

    def get_vr_id(self):
        return database.new_verification_result_id()


#==================================================================
# worker class for the pipeline
#==================================================================
class Worker(Agent):
    """ Represents a worker, knows how to do jobs he is given, create results and rsync them back """
    def __init__(self, num=0, uuid=''):
        super(Worker, self).__init__(name='worker', num=num, uuid=uuid)

    def run(self):
        """ Start to listen, tunnels should be open and ready """
        self.connect()
        self.bsd.watch(TUBE_JOBS)
        self.bsd.ignore("default")
        self.get_jobs()

    def get_jobs(self):
        """ Endless loop that awaits jobs to run """
        while not self.halt:
            self.logger.info("Waiting for jobs...")
            job = self.bsd.reserve()
            self.job = job
            
            # if appears that there is a 120sec re-birth of jobs that have been reserved
            # and I do not want to put an artificial time limit, so let's bury jobs
            # when we get them
            job.bury()
            self.comm.send_msg("running", job.body)

            # got a job -----
            # update the repository, attempt to run the job and return the results to the director
            try:
                jobmsg = Message(string=job.body)
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
            # check to see if this is a verifier or an actual test
            try:
                name,leader,num,version = database.parse_kim_code(jobmsg.job[0])
            except InvalidKIMID as e:
                # we were not given a valid kimid
                self.logger.error("Could not parse {} as a valid KIMID".format(jobmsg.job[0]))
                self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                job.delete()
                continue

            if leader == "VT" or leader == "VM":
                try:
                    self.logger.info("rsyncing to repo %r", jobmsg.job+jobmsg.depends)
                    rsync_tools.worker_verification_read(*jobmsg.job, depends=jobmsg.depends)
                    self.make_all()

                    verifier_kcode, subject_kcode = jobmsg.job
                    verifier = kimobjects.Verifier(verifier_kcode)
                    subject  = kimobjects.Subject(subject_kcode)

                    self.logger.info("Running (%r,%r)",verifier,subject)
                    result = runner.run_test_on_model(verifier,subject)

                    #create the verification result object (will be written)
                    vr = kimobjects.VerificationResult(jobmsg.jobid, results = result, search=False)

                    self.logger.info("rsyncing results %r", jobmsg.jobid)
                    rsync_tools.worker_verification_write(jobmsg.jobid)
                    self.logger.info("sending result message back")
                    self.job_message(jobmsg, results=result, tube=TUBE_RESULTS)
                    job.delete()

                # could be that a dependency has not been met.
                # put it back on the queue to wait
                except PipelineDataMissing as e:
                    if job.stats()['age'] < 5*PIPELINE_JOB_TIMEOUT:
                        self.logger.error("Run failed, missing data.  Returning to queue... (%r)" % e)
                        job.release(delay=PIPELINE_JOB_TIMEOUT)
                    else:
                        self.logger.error("Run failed, missing data. Lifetime has expired, deleting (%r)" % e)
                        job.delete()

                # another problem has occurred.  just remove the job
                # and send the error back along the error queue
                except Exception as e:
                    self.logger.error("Run failed, deleting... %r" % e)
                    self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                    job.delete()
            else:
                try:
                    self.logger.info("rsyncing to repo %r %r", jobmsg.job,jobmsg.depends)
                    rsync_tools.worker_test_result_read(*jobmsg.job, depends=jobmsg.depends)
                    self.make_all()

                    test_kcode, model_kcode = jobmsg.job
                    test = kimobjects.Test(test_kcode)
                    model = kimobjects.Model(model_kcode)

                    self.logger.info("Running (%r,%r)",test,model)
                    result = runner.run_test_on_model(test,model)

                    #create the test result object (will be written)
                    tr = kimobjects.TestResult(jobmsg.jobid, results = result, search=False)

                    self.logger.info("rsyncing results %r", jobmsg.jobid)
                    rsync_tools.worker_test_result_write(jobmsg.jobid)
                    self.logger.info("sending result message back")
                    self.job_message(jobmsg, results=result, tube=TUBE_RESULTS)
                    job.delete()

                # could be that a dependency has not been met.
                # put it back on the queue to wait
                except PipelineDataMissing as e:
                    if job.stats()['age'] < 5*PIPELINE_JOB_TIMEOUT:
                        self.logger.error("Run failed, missing data.  Returning to queue... (%r)" % e)
                        job.release(delay=PIPELINE_JOB_TIMEOUT)
                    else:
                        self.logger.error("Run failed, missing data. Lifetime has expired, deleting (%r)" % e)
                        job.delete()

                # another problem has occurred.  just remove the job
                # and send the error back along the error queue
                except Exception as e:
                    self.logger.error("Run failed, deleting... %r" % e)
                    self.job_message(jobmsg, errors=e, tube=TUBE_ERRORS)
                    job.delete()
                    raise
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
        self.bsd.use("web_updates")
        self.bsd.put(simplejson.dumps({"kimid": kimid, "priority":"normal", "status":"approved"}))


#=======================================================
# MAIN
#=======================================================
pipe = {}
procs = {}
def signal_handler(): #signal, frame):
    print "Sending signal to flush, wait 1 sec..."
    for p in pipe.values():
        p.halt = True
        p.exit_safe()
    for p in procs.values():
        p.join(timeout=1)
    sys.exit(1)

open_ports(GLOBAL_PORT, PORT_RX, PORT_TX, GLOBAL_USER, GLOBAL_HOST, GLOBAL_IP)

if __name__ == "__main__":
    import sys 
    UUID = uuid.uuid4()

    if len(sys.argv) > 1:
        if sys.argv[1] != "site" and sys.argv[1] != "agent":
            thrds = cpu_count() 
            for i in range(thrds):
                if sys.argv[1] == "director":
                    pipe[i] = Director(num=i, uuid=UUID)
                    procs[i] = Thread(target=Director.run, args=(pipe[i],), name='director-%i'%i)
                elif sys.argv[1] == "worker":
                    pipe[i] = Worker(num=i, uuid=UUID)
                    procs[i] = Thread(target=Worker.run, args=(pipe[i],), name='worker-%i'%i)
            for i in range(thrds):
                procs[i].daemon = True
                procs[i].start()

            try:
                while True:
                    for i in range(thrds):
                        procs[i].join(timeout=1.0)
            except (KeyboardInterrupt, SystemExit):
                signal_handler()#signal.SIGINT, None)
            
        elif sys.argv[1] == "site":
            obj = Site()
            obj.run()
            obj.send_update(sys.argv[2])
    else:
        print "Specify {worker|director|site}"
