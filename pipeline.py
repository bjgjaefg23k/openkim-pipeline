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
import time, simplejson, traceback, sys, zmq
import rsync_tools, runner, kimapi, database 
import models as modelslib
logger = logger.getChild("pipeline")

PIPELINE_WAIT    = 1
PIPELINE_TIMEOUT = 60
PIPELINE_MSGSIZE = 2**20
PIPELINE_JOB_TIMEOUT = 3600*24 #one day 

TUBE_UPDATE  = "updates"
TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_ERRORS  = "errors"
TUBE_LOG     = "logs"

KEY_JOBID    = "jobid"
KEY_PRIORITY = "priority"
KEY_JOB      = "job"
KEY_RESULTS  = "results"
KEY_ERRORS   = "errors"
KEY_DEPENDS  = "depends"
KEY_CHILD    = "child"
KEY_STATUS   = "status"

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
        # decide on the port order
        self.port_tx = PORT_TX
        self.port_rx = PORT_RX 
        self.con = zmq.Context()
 
        # open both the rx/tx lines, bound
        self.sock_tx = self.con.socket(zmq.PUB)
        self.sock_tx.connect("tcp://127.0.0.1:"+str(self.port_tx))
 
        self.sock_rx = self.con.socket(zmq.SUB)
        self.sock_rx.setsockopt(zmq.SUBSCRIBE, "")
        self.sock_rx.connect("tcp://127.0.0.1:"+str(self.port_rx))
 
        super(Communicator, self).__init__()
        self.daemon = True
 
    def run(self):
        while 1:
            obj = self.sock_rx.recv_pyobj()

    def send_msg(self, tube, msg):
        self.sock_tx.send_pyobj([tube, msg])


#==================================================================
# the logging handler for beanstalkd queues
#==================================================================
class BeanstalkHandler(logging.Handler):
    """ A beanstalk logging handler """
    def __init__(self,bsd):
        self.bsd = bsd
        self.info = runner.getboxinfo()
        super(BeanstalkHandler,self).__init__()

    def emit(self,record):
        """ Send the message """
        err_message = self.format(record)
        message = self.info.copy()
        message['message'] = err_message
        self.bsd.use(TUBE_LOG)
        self.bsd.put(simplejson.dumps(message))

class Message(object):
    """Message format for the queue system:
        "jobid":    id assigned from the director
        "priority": a string priority
        "job":      (testid, modelid, testresult id)
        "results":  the json message produced by the run
        "errors":   the exception caught and returned as a string
        "depends":  a list of tuples of jobs
    """
    def __init__(self, string=None, jobid=None,
            priority=None, job=None, results=None,
            errors=None, depends=None, child=None,
            status=None):
        if string is not None:
            self.msg_from_string(string)
        else:
            self.jobid = jobid
            self.priority = priority
            self.job = job
            self.results = results
            self.errors = errors
            self.depends = depends
            self.child = child
            self.status = status

    def todict(self):
        return {KEY_JOBID: self.jobid, KEY_PRIORITY: self.priority,
            KEY_JOB: self.job, KEY_RESULTS: self.results, KEY_ERRORS: self.errors,
            KEY_DEPENDS: self.depends, KEY_CHILD: self.child, KEY_STATUS: self.status} 

    def __repr__(self):
        """ The repr of the string is a ``simplejson.dumps`` """
        return simplejson.dumps(self.todict())

    def msg_from_string(self,string):
        """ Generate a Message from a string """
        dic = simplejson.loads(string)
        self.jobid = dic[KEY_JOBID]
        self.priority = dic[KEY_PRIORITY]
        self.job = dic[KEY_JOB]
        self.results = dic[KEY_RESULTS]
        self.errors = dic[KEY_ERRORS]
        self.depends = dic[KEY_DEPENDS]
        self.child = dic[KEY_CHILD]
        self.status = dic[KEY_STATUS]

def ll(iterator):
    return len(list(iterator))

#==================================================================
# director class for the pipeline
#==================================================================
class Director(object):
    """ The Director object, knows to listen to incoming jobs, computes dependencies
    and passes them along to workers
    """
    def __init__(self, num=0):
        self.ip   = GLOBAL_IP
        self.port = GLOBAL_PORT
        self.timeout = PIPELINE_TIMEOUT
        self.msg_size = PIPELINE_MSGSIZE
        self.logger = logger.getChild("director-%i" % num)
        self.boxinfo = runner.getboxinfo()
        self.num = num
        self.halt = False

        self.comm = Communicator()
        self.comm.start()

    def run(self):
        """ connect and grab the job thread """
        self.connect_to_daemon()
        self.get_updates()

    def connect_to_daemon(self):
        """ try to connect to the daemon, or launch one if we timeout """
        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except bean.SocketError:
            # We failed to connect, this is really bad
            self.logger.error("Failed to connect to beanstalk queue after launching ssh")

        self.logger.info("Director ready")

        # we want to get updates from the webserver on the 'update' tube
        self.bsd.watch(TUBE_UPDATE)
        self.bsd.ignore("default")

        #attach the beanstalk logger
        beanstalk_handler = BeanstalkHandler(self.bsd)
        beanstalk_handler.setLevel(BEANSTALK_LEVEL)
        beanstalk_handler.setFormatter(log_formatter)
        self.logger.addHandler(beanstalk_handler)

    def disconnect_from_daemon(self):
        """ close and kill """
        self.bsd.close()
        self.daemon.kill()

    def get_tr_id(self):
        """ Generate a TR id """
        return database.new_test_result_id()

    def get_vr_id(self):
        """ Get VR id from database """
        return database.new_verification_result_id()

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
            self.request = request

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
            self.request = None
        
    def exit_safe(self):
        if hasattr(self, 'request') and self.request is not None:
            self.request.delete()

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
            test = modelslib.VerificationTest(kimid)
            models = modelslib.Test.all()
            tests = [test]*ll(models)
        elif leader=="VM":
            # we have a new VM

            # first pull it and build it
            rsync_tools.director_new_model_verification_read(kimid)
            self.make_all()

            #for all of the models, run a job
            test = modelslib.VerificationModel(kimid)
            models = modelslib.Model.all()
            tests = [test]*ll(models)
        else:
            if status == "approved":
                if leader=="TE":
                    # we have a new TE, first pull it and build it
                    rsync_tools.director_new_test_read(kimid)
                    self.make_all()

                    # for all of the models, add a job
                    test = modelslib.Test(kimid)
                    models = test.models
                    tests = [test]*ll(models)
                elif leader=="MO":
                    # we have a model, first pull it and build it
                    rsync_tools.director_new_model_read(kimid)
                    self.make_all()

                    # for all of the tests, add a job
                    model = modelslib.Model(kimid)
                    tests = model.tests
                    models = [model]*ll(tests)
                elif leader=="TD":
                    # we have a new test driver, first pull and build it
                    rsync_tools.director_new_test_driver_read(kimid)
                    self.make_all()

                    # if it is a new version of an existing test driver, hunt
                    # down all of the tests that use it and launch their
                    # corresponding jobs
                    driver = modelslib.TestDriver(kimid)
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
                    driver = modelslib.ModelDriver(kimid)
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
                    tests = modelslib.VertificationTest.all()
                    models = [modelslib.Test(kimid, search=False)]*ll(tests)
                elif leader=="MO":
                    # a pending model
                    rsync_tools.director_model_verification_read(kimid)
                    self.make_all()

                    # run against all model verifications
                    tests = modelslib.VertificationModel.all()
                    models = [modelslib.Model(kimid, search=False)]*ll(tests)

                elif leader=="TD":
                    # a pending test driver
                    pass
                    # no verifications really... ? FIXME
                elif leader=="MD":
                    # a pending model driver
                    pass
                    # no verifications really... ? FIXME
                else:
                    self.logger.error("Tried to update an invalid KIM ID!: %r",kimid)
                checkmatch = False 

        for test, model in zip(tests,models):
            if checkmatch and kimapi.valid_match(test,model):
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
            if TRs:
                TR_ids = tuple(map(str,TRs))
            else:
                TR_ids = ()

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
                        depids.append(self.check_dependencies_and_push(str(t),str(m),priority/10,status,child=(str(test),str(model),trid)))

            msg = Message(job=(str(test),str(model)),jobid=trid, child=child, depends=TR_ids+tuple(depids), status=status) 
            self.job_message(msg)

        return depids

    def job_message(self, jobmsg, tube=TUBE_JOBS):
        """ Send back a job message """
        dic = jobmsg.todict()
        dic.update(self.boxinfo)
        msg = simplejson.dumps(dic)
        self.bsd.use(tube)
        self.bsd.put(msg)
        self.comm.send_msg(tube, msg)

    def make_object(self, kimid):
        self.logger.debug("Building the source for %r", kimid)
        kimobj = modelslib.KIMObject(kimid)
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

    def halt(self):
        self.disconnect_from_daemon()


#==================================================================
# worker class for the pipeline
#==================================================================
class Worker(object):
    """ Represents a worker, knows how to do jobs he is given, create results and rsync them back """
    def __init__(self, num=0):
        self.ip   = GLOBAL_IP
        self.port = GLOBAL_PORT
        self.timeout = PIPELINE_TIMEOUT
        self.logger = logger.getChild("worker-%i"% num)
        self.boxinfo = runner.getboxinfo()
        self.halt = False

        self.comm = Communicator()
        self.comm.start()

    def run(self):
        """ Start to listen, tunnels should be open and ready """
        try:
            self.start_listen()
        except bean.SocketError:
            # We failed to connect, this is really bad
            self.logger.error("Failed to connect to beanstalk queue after launching ssh")

        self.logger.info("Connected to daemon")
        #attach the beanstalk logger
        beanstalk_handler = BeanstalkHandler(self.bsd)
        beanstalk_handler.setLevel(BEANSTALK_LEVEL)
        beanstalk_handler.setFormatter(log_formatter)
        self.logger.addHandler(beanstalk_handler)

        self.get_jobs()

    def start_listen(self):
        """ Start to listen and connect to the TUBE_JOBS """
        # connect to the daemon we created
        self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get jobs from the 'jobs' tube
        self.bsd.watch(TUBE_JOBS)
        self.bsd.ignore("default")

    def job_message(self, jobmsg, errors=None, results=None, tube=TUBE_ERRORS):
        """ Send back a job message """
        resultsmsg = Message(jobid=jobmsg.jobid, priority=jobmsg.priority,
                job=jobmsg.job, results=results, errors=repr(errors))
        dic = resultsmsg.todict()
        dic.update(self.boxinfo)
        msg = simplejson.dumps(dic)
        self.bsd.use(tube)
        self.bsd.put(msg)
        self.comm.send_msg(tube, msg)

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
            # update the repository, attempt to run the job
            # and return the results to the director
            #repo.rsync_update()
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
                    verifier = modelslib.Verifier(verifier_kcode)
                    subject  = modelslib.Subject(subject_kcode)

                    self.logger.info("Running (%r,%r)",verifier,subject)
                    result = runner.run_test_on_model(verifier,subject)

                    #create the verification result object (will be written)
                    vr = modelslib.VerificationResult(jobmsg.jobid, results = result, search=False)

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
                    self.logger.info("rsyncing to repo %r", jobmsg.job+jobmsg.depends)
                    rsync_tools.worker_test_result_read(*jobmsg.job, depends=jobmsg.depends)
                    self.make_all()

                    test_kcode, model_kcode = jobmsg.job
                    test = modelslib.Test(test_kcode)
                    model = modelslib.Model(model_kcode)

                    self.logger.info("Running (%r,%r)",test,model)
                    result = runner.run_test_on_model(test,model)

                    #create the test result object (will be written)
                    tr = modelslib.TestResult(jobmsg.jobid, results = result, search=False)

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
            self.job = None
            self.jobsmsg = None
 
    def exit_safe(self): 
        # we got the signal to shutdown, so release the job first
        if hasattr(self, 'job') and self.job is not None:
            self.job.delete()
            if hasattr(self, 'jobmsg') and self.jobmsg is not None: 
                self.job_message(self.jobmsg, errors="Caught SIGINT and killed", tube=TUBE_ERRORS)
    
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


class Site(object):
    """ False stand in for the website, pushes TR ids for us and can update models or tests """
    def __init__(self):
        self.ip   = GLOBAL_IP
        self.port = GLOBAL_PORT
        self.timeout = PIPELINE_TIMEOUT
        self.msg_size = PIPELINE_MSGSIZE
        self.logger = logger.getChild("website")

    def run(self):
        self.connect_to_daemon()

    def connect_to_daemon(self):
        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except bean.SocketError:
            # We failed to connect, this is really bad
            self.logger.error("Failed to connect to beanstalk queue after launching ssh")

        self.logger.info("Website ready")
        self.logger.info("Pushing jobs")

    def send_update(self, kimid):
        self.bsd.use("web_updates")
        self.bsd.put(simplejson.dumps({"kimid": kimid, "priority":"normal", "status":"approved"}))

pipe = {}
procs = {}
def signal_handler(): #signal, frame):
    print "Sending signal to flush, wait 1 sec..."
    for p in pipe.values():
        p.halt = True
        p.exit_safe()
    for p in procs.values():
        p.join(1)
    sys.exit(1)
#signal.signal(signal.SIGINT, signal_handler)

open_ports(GLOBAL_PORT, PORT_RX, PORT_TX, GLOBAL_USER, GLOBAL_HOST, GLOBAL_IP)

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        if sys.argv[1] != "site":
            thrds = cpu_count() 
            for i in range(thrds):
                if sys.argv[1] == "director":
                    pipe[i] = Director(i)
                    procs[i] = Thread(target=Director.run, args=(pipe[i],), name='director-%i'%i)
                elif sys.argv[1] == "worker":
                    pipe[i] = Worker(i)
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
