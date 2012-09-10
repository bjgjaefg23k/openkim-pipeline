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
import models as modelslib
import database
import beanstalkc as bean
from subprocess import check_call, Popen, PIPE
import subprocess
from multiprocessing import Process, cpu_count
import urllib
import time
import simplejson
import rsync_tools
import models
import database
import runner
import traceback
logger = logger.getChild("pipeline")

import simplejson

PIPELINE_WAIT    = 10
PIPELINE_TIMEOUT = 60
PIPELINE_MSGSIZE = 2**20
PIPELINE_JOB_TIMEOUT = 3600 #one hour
TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_UPDATE  = "updates"
TUBE_ERRORS  = "errors"
TUBE_LOG     = "logs"
TUBE_TR_IDS  = "tr_ids"
TUBE_VR_IDS  = "vr_ids"

KEY_JOBID    = "jobid"
KEY_PRIORITY = "priority"
KEY_JOB      = "job"
KEY_RESULTS  = "results"
KEY_ERRORS   = "errors"
KEY_DEPENDS  = "depends"
KEY_CHILD    = "child"
KEY_STATUS   = "status"

BEANSTALK_LEVEL = logging.INFO

class BeanstalkHandler(logging.Handler):
    """ A beanstalk logging handler """
    def __init__(self,bsd):
        self.bsd = bsd
        self.info = self.getinfo()
        super(BeanstalkHandler,self).__init__()
    def getinfo(self):
        info = {}
        things = ['sitename','username','boxtype','ipaddr']

        for thing in things:
            info[thing] = open(os.path.join('/persistent',thing)).read().strip()
        return info

    def emit(self,record):
        """ Send the message """
        err_message = self.format(record)
        self.bsd.use(TUBE_LOG)
        message = self.info.copy()
        message['message'] = err_message
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

    def __repr__(self):
        """ The repr of the string is a ``simplejson.dumps`` """
        return simplejson.dumps({KEY_JOBID: self.jobid, KEY_PRIORITY: self.priority,
            KEY_JOB: self.job, KEY_RESULTS: self.results, KEY_ERRORS: self.errors,
            KEY_DEPENDS: self.depends, KEY_CHILD: self.child, KEY_STATUS: self.status})

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

class Director(object):
    """ The Director object, knows to listen to incoming jobs, computes dependencies
    and passes them along to workers
    """
    def __init__(self):
        self.ip   = GLOBAL_IP
        self.port = GLOBAL_PORT
        self.timeout = PIPELINE_TIMEOUT
        self.msg_size = PIPELINE_MSGSIZE
        self.remote_user = GLOBAL_USER
        self.remote_addr = GLOBAL_HOST
        self.logger = logger.getChild("director")

    def run(self):
        """ connect and grab the job thread """
        self.connect_to_daemon()
        self.job_thrd  = Process(target=Director.get_updates(self))

    def launch_screen(self):
        """ Launch a screened ssh connection """
        self.ssh = Popen("screen -dm ssh -i /persistent/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -L{}:{}:{} {}@{}".format(
            self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
        self.logger.info("Waiting to connect to beanstalkd")
        time.sleep(PIPELINE_WAIT)

    def connect_to_daemon(self):
        """ try to connect to the daemon, or launch one if we timeout """
        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except bean.SocketError:
            self.logger.info("No daemon found, starting on %r", self.remote_addr)
            # no need to start the daemon anymore for debug.  It's always going
            #self.daemon = Popen("ssh {}@{} \"screen -dm beanstalkd -l {} -p {} -z {} -b beanlog -f 0\"".format(
            #    self.remote_user, self.remote_addr, self.ip, self.port, self.msg_size), shell=True)
            self.launch_screen()
            try:
                self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
            except bean.SocketError:
                # We failed to connect twice, this is really bad
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
        """ Get a TR id from the TUBE_TR_IDS """
        self.logger.info("Requesting new TR id")
        bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        bsd.watch(TUBE_TR_IDS)
        request = bsd.reserve()
        tr_id = request.body
        request.delete()
        bsd.close()
        return tr_id

    def get_vr_id(self):
        """ Get a VR id from TUBE_VR_IDS """
        self.logger.info("Requesting new VR id")
        bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        bsd.watch(TUBE_VR_IDS)
        request = bsd.reserve()
        vr_id = request.body
        request.delete()
        bsd.close()
        return vr_id

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
        while 1:
            self.logger.info("Director Waiting for message...")
            request = self.bsd.reserve()

            # got a request to update a model or test
            # from the website (or other trusted place)
            if request.stats()['tube'] == TUBE_UPDATE:
                # update the repository,send it out as a job to compute
                try:
                    rsync_tools.full_sync()
                    self.push_jobs(simplejson.loads(request.body))
                except Exception as e:
                    tb = traceback.format_exc()
                    self.logger.error("Director had an error on update: {}\n {}".format(e, tb))

            request.delete()

    def priority_to_number(self,priority):
        priorities = {"immediate": 0, "very high": 0.01, "high": 0.1,
                      "normal": 1, "low": 10, "very low": 100}
        if priority not in priorities.keys():
            priority = "normal"
        return priorities[priority]

    def push_jobs(self, update):
        """ Push all of the jobs that need to be done given an update """
        self.bsd.use(TUBE_JOBS)
        kimid = update['kimid']
        status = update['status']
        priority_factor = self.priority_to_number(update['priority'])

        name,leader,num,version = database.parse_kim_code(kimid)

        # try to build the kimid before sending jobs
        if self.make_object(kimid) == 0:
            rsync_tools.director_build_write(kimid)
        else:
            self.logger.error("Could not build %r", kimid)
            self.bsd.use(TUBE_ERRORS)
            self.bsd.put(simplejson.dumps({"error": "Could not build %r" % kimid}))
            return

        if leader=="VT":
            test = modelslib.VerificationTest(kimid)
            models = modelslib.Test.all()
            tests = [test]
        elif leader=="VM":
            test = modelslib.VerificationModel(kimid)
            models = modelslib.Model.all()
            tests = [test]
        else:
            if status == "approved":
                if leader=="TE":
                    test = modelslib.Test(kimid)
                    models = test.models
                    tests = [test]
                elif leader=="MO":
                    model = modelslib.Model(kimid)
                    models = [model]
                    tests = model.tests
                else:
                    self.logger.error("Tried to update an invalid KIM ID!: %r",kimid)
            if status == "pending":
                if leader=="TE":
                    tests = modelslib.VertificationTest.all()
                    models = [modelslib.Test(kimid)]
                elif leader=="MO":
                    tests = modelslib.VertificationModel.all()
                    models = [modelslib.Model(kimid)]
                else:
                    self.logger.error("Tried to update an invalid KIM ID!: %r",kimid)

        for test in tests:
            for model in models:
                priority = int(priority_factor*database.test_model_to_priority(test,model) * 1000000)
                self.check_dependencies_and_push(test,model,priority,status)


    def check_dependencies_and_push(self, test, model, priority, status, child=None):
        """ Check dependencies, and push them first if necessary """
        # run the test in its own directory
        depids = []
        with test.in_dir():
            #grab the input file
            ready, TRs, PAIRs = test.dependency_check(model)
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

            self.bsd.use(TUBE_JOBS)
            self.bsd.put(repr(Message(job=(str(test),str(model)),jobid=trid, child=child, depends=TR_ids+tuple(depids), status=status)), priority=priority)

        return depids

    def make_object(self, kimid):
        self.logger.debug("Building the source for %r", kimid)
        kimobj = modelslib.KIMObject(kimid)
        with kimobj.in_dir():
            try:
                subprocess.check_call("make")
            except subprocess.CalledProcessError as e:
                return 1
            return 0

    def halt(self):
        self.disconnect_from_daemon()



class Worker(object):
    """ Represents a worker, knows how to do jobs he is given, create results and rsync them back """
    def __init__(self):
        self.remote_user = GLOBAL_USER
        self.remote_addr = GLOBAL_HOST
        self.ip          = GLOBAL_IP
        self.timeout = PIPELINE_TIMEOUT
        self.port = GLOBAL_PORT
        self.logger = logger.getChild("worker")

    def run(self):
        """ Start to listen, launch the daemon if we timeout """
        # if we can't already connect to the daemon on localhost,
        # open an ssh tunnel to the daemon and start the beanstalk
        try:
            self.start_listen()
        except:
            self.ssh = Popen("screen -dm ssh -i /persistent/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            self.logger.info("Waiting to connect to beanstalkd")
            time.sleep(PIPELINE_WAIT)
            self.start_listen()

        self.logger.info("Connected to daemon")
        self.get_jobs()

        #attach the beanstalk logger
        beanstalk_handler = BeanstalkHandler(self.bsd)
        beanstalk_handler.setLevel(BEANSTALK_LEVEL)
        beanstalk_handler.setFormatter(log_formatter)
        self.logger.addHandler(beanstalk_handler)

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
        self.bsd.use(tube)
        self.bsd.put(repr(resultsmsg))


    def get_jobs(self):
        """ Endless loop that awaits jobs to run """
        while 1:
            self.logger.info("Waiting for jobs...")
            job = self.bsd.reserve()

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

            # check to see if this is a verifier or an actual test
            try:
                name,leader,num,version = database.parse_kim_code(jobmsg.job[0])
            except InvalidKIMID as e:
                # we were not given a valid kimid
                self.logger.error("Could not parse {} as a valid KIMID".format(jobmsg.job[0]))
                self.job_message(jobmsg, errors=e)
                job.delete()
                continue

            if leader == "VT" or leader == "VM":
                try:
                    self.logger.info("rsyncing to repo %r", jobmsg.job+jobmsg.depends)
                    rsync_tools.worker_test_result_read(*jobmsg.job, depends=jobmsg.depends)

                    verifier_kcode, subject_kcode = jobmsg.job
                    verifier = models.Verifier(verifier_kcode)
                    subject  = models.Subject(subject_kcode)

                    self.logger.info("Running (%r,%r)",verifier,subject)
                    result = runner.run_verifier_on_subject(verifier,subject)

                    #create the verification result object (will be written)
                    vr = models.VerificationResult(jobmsg.jobid, results = result, search=False)

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
                    self.job_message(jobmsg, errors=e)
                    job.delete()



            else:
                try:
                    self.logger.info("rsyncing to repo %r", jobmsg.job+jobmsg.depends)
                    rsync_tools.worker_test_result_read(*jobmsg.job, depends=jobmsg.depends)

                    test_kcode, model_kcode = jobmsg.job
                    test = models.Test(test_kcode)
                    model = models.Model(model_kcode)

                    self.logger.info("Running (%r,%r)",test,model)
                    result = runner.run_test_on_model(test,model)

                    #create the test result object (will be written)
                    tr = models.TestResult(jobmsg.jobid, results = result, search=False)

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
                    self.job_message(jobmsg, errors=e )
                    job.delete()


class Site(object):
    """ False stand in for the website, pushes TR ids for us and can update models or tests """
    def __init__(self):
        self.ip   = GLOBAL_IP
        self.port = GLOBAL_PORT
        self.timeout = PIPELINE_TIMEOUT
        self.msg_size = PIPELINE_MSGSIZE
        self.remote_user = GLOBAL_USER
        self.remote_addr = GLOBAL_HOST
        self.logger = logger.getChild("website")

    def run(self):
        self.connect_to_daemon()

    def connect_to_daemon(self):
        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except:
            self.ssh = Popen("screen -dm ssh -i /persistent/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            time.sleep(1)
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        self.logger.info("Website ready")
        self.logger.info("Pushing jobs")

        self.bsd.use(TUBE_TR_IDS)
        for i in range(10):
            self.bsd.put(database.new_tr_kimid())


    def send_update(self, kimid):
        self.bsd.use(TUBE_UPDATE)
        self.bsd.put(simplejson.dumps({"kimid": kimid, "priority":"normal", "status":"approved"}))




if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        for i in range(cpu_count()):
            if sys.argv[1] == "director":
                obj = Director()
                thrd = Process(target=Director.run(obj))
            elif sys.argv[1] == "worker":
                obj = Worker()
                thrd = Process(target=Worker.run(obj))
            elif sys.argv[1] == "site":
                obj = Site()
                thrd = Process(target=Site.run(obj))
                obj.send_update("TB_Khakshouri_F_Fe__MO_853979044095_000")
    else:
        print "Specify {worker|director|site}"
        exit(1)
