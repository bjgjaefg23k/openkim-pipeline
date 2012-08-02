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
from multiprocessing import Process
import urllib
import time
import simplejson
import rsync_tools
import models
import database
import runner
logger = logger.getChild("pipeline")

import simplejson

PIPELINE_WAIT    = 10
PIPELINE_TIMEOUT = 60
PIPELINE_MSGSIZE = 2**20
TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_UPDATE  = "updates"
TUBE_ERRORS  = "errors"
TUBE_TR_IDS  = "tr_ids"
TUBE_VR_IDS  = "vr_ids"

KEY_JOBID    = "jobid"
KEY_PRIORITY = "priority"
KEY_JOB      = "job"
KEY_RESULTS  = "results"
KEY_ERRORS   = "errors"
KEY_DEPENDS  = "depends"
KEY_CHILD    = "child"


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
            errors=None, depends=None, child=None):
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

    def __repr__(self):
        """ The repr of the string is a ``simplejson.dumps`` """
        return simplejson.dumps({KEY_JOBID: self.jobid, KEY_PRIORITY: self.priority,
            KEY_JOB: self.job, KEY_RESULTS: self.results, KEY_ERRORS: self.errors, 
            KEY_DEPENDS: self.depends, KEY_CHILD: self.child})

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

    def connect_to_daemon(self):
        """ try to connect to the daemon, or launch one if we timeout """
        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except:
            self.logger.info("No daemon found, starting on %r", self.remote_addr)
            self.daemon = Popen("ssh {}@{} \"screen -dm beanstalkd -l {} -p {} -z {} -b beanlog -f 0\"".format(
                self.remote_user, self.remote_addr, self.ip, self.port, self.msg_size), shell=True)
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            self.logger.info("Waiting to connect to beanstalkd")
            time.sleep(PIPELINE_WAIT)
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        self.logger.info("Director ready")
        # we want to get updates from the webserver on the 'update' tube
        # and post the jobs on 'jobs' tube, receive on the 'results' and 'error' tube
        self.bsd.watch(TUBE_UPDATE)
        self.bsd.watch(TUBE_RESULTS)
        self.bsd.watch(TUBE_ERRORS)
        self.bsd.ignore("default")


    def disconnect_from_daemon(self):
        """ close and kill """
        self.bsd.close()
        self.daemon.kill()

    def get_tr_id(self):
        """ Get a TR id from the TUBE_TR_IDS """
        bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        bsd.watch(TUBE_TR_IDS)
        request = bsd.reserve()
        tr_id = request.body
        request.delete()
        bsd.close()
        return tr_id

    def get_vr_id(self):
        """ Get a VR id from TUBE_VR_IDS """
        bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        bsd.watch(TUBE_VR_IDS)
        request = bsd.reserve()
        vr_id = request.body
        request.delete()
        bsd.close()
        return vr_id

    def get_updates(self):
        """ Endless loop that waits for updates """
        while 1:
            request = self.bsd.reserve()

            # got a request to update a model or test
            # from the website (or other trusted place)
            if request.stats()['tube'] == TUBE_UPDATE:
                # update the repository,send it out as a job to compute
                rsync_tools.full_sync()
                self.push_jobs(simplejson.loads(request.body))

            # got word from a worker that a job is complete
            if request.stats()['tube'] == TUBE_RESULTS:
                ret = Message(string=request.body) 
                self.logger.info("Finished %r ...", ret.job)
                self.logger.info("Results returned: %r", ret.results) 
                    
            if request.stats()['tube'] == TUBE_ERRORS:
                ret = Message(string=request.body)
                self.logger.error("Errors occured: %r", ret.errors)

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
        priority_factor = self.priority_to_number(update['priority'])

        name,leader,num,version = database.parse_kim_code(kimid)

        #We either have a test or a model
        if leader=="TE":
            test = modelslib.Test(kimid)
            tests = [test]
            models = test.models
        elif leader=="MO":
            model = modelslib.Model(kimid)
            tests = model.tests
            models = [model]
        else:
            self.logger.error("Tried to update an invalid KIM ID!: %r",kimid)

        for test in tests:
            for model in models: 
                priority = int(priority_factor*database.test_model_to_priority(test,model) * 2**15)
                self.check_dependencies_and_push(test,model,priority)

    def check_dependencies_and_push(self, test, model, priority, child=None):
        """ Check dependencies, and push them first if necessary """
        test_dir = test.path
        # run the test in its own directory
        with test.in_dir():
            #grab the input file
            ready, TRs, PAIRs = test.dependency_check()
            TR_ids = map(str,TRs)

            self.logger.info("Requesting new TR id")
            trid = self.get_tr_id()
            self.logger.info("Submitting job <%s, %s, %s> priority %i" % (test, model, trid, priority))

            if not ready:
                # Some test results are required
                depids = []
                for (t,m) in PAIRs:
                    self.logger.info("Submitting dependency <%s, %s>" % (t, m))
                    # FIXME - Maybe force higher priority?
                    depids.append(self.check_dependencies_and_push(str(t),str(m),priority,child=(str(test),str(model),trid)))
                # Delayed-put and bury, wait for dependencies to resolve FIXME
                self.bsd.use(TUBE_JOBS)
                self.bsd.put(repr(Message(job=(str(test),str(model)),jobid=trid, child=child, depends=TR_ids+tuple(depids))), priority=priority)
            else:
                self.bsd.use(TUBE_JOBS)
                self.bsd.put(repr(Message(job=(str(test),str(model)),jobid=trid, child=child, depends=TR_ids)), priority=priority)

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
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            self.logger.info("Waiting to connect to beanstalkd")
            time.sleep(PIPELINE_WAIT)
            self.start_listen()

        self.logger.info("Connected to daemon")
        self.get_jobs()

    def start_listen(self):
        """ Start to listen and connect to the TUBE_JOBS """
        # connect to the daemon we created
        self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get jobs from the 'jobs' tube 
        self.bsd.watch(TUBE_JOBS)
        self.bsd.ignore("default")
        
    def get_jobs(self):
        """ Endless loop that awaits jobs to run """
        while 1:
            self.logger.info("Waiting for jobs...")
            job = self.bsd.reserve()
            job.bury()

            # got a job -----
            # update the repository, attempt to run the job
            # and return the results to the director
            #repo.rsync_update()
            jobmsg = Message(string=job.body)
            try:
                self.logger.info("rsyncing to repo %r", jobmsg.job+jobmsg.depends)
                rsync_tools.worker_test_result_read(*jobmsg.job, depends=jobmsg.depends)
                self.logger.info("Running %r ...", jobmsg.jobid)
               
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
                resultsmsg = Message(jobid=jobmsg.jobid, priority=jobmsg.priority,
                        job=jobmsg.job, results=result, errors=None)
                self.bsd.use(TUBE_RESULTS)
                self.bsd.put(repr(resultsmsg))
                job.delete()
            
            except Exception as e:
                self.logger.error("Run failed, removing... %r" % e)
                resultsmsg = Message(jobid=jobmsg.jobid, priority=jobmsg.priority,
                        job=jobmsg.job, results=None, errors=repr(e))
                self.bsd.use(TUBE_ERRORS)
                self.bsd.put(repr(resultsmsg))
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
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(
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
        self.bsd.put(simplejson.dumps({"kimid": kimid, "priority":"normal"}))




if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        if sys.argv[1] == "director":
            obj = Director()
            obj.run()
        elif sys.argv[1] == "worker":
            obj = Worker()
            obj.run()
        elif sys.argv[1] == "site":
            obj = Site()
            obj.run()
            obj.send_update("MO_607867530001_000")
    else:
        print "Specify {worker|director|site}"
        exit(1)
