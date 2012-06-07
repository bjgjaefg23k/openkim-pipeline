import repository as repo
import beanstalkc as bean 
from subprocess import check_call, Popen, PIPE
from multiprocessing import Process
import runner
import urllib
import time
import simplejson
import template
from config import *
from pipeline_global import *
logger = logger.getChild("pipeline")

class Director(object):
    def __init__(self):
        self.ip   = GLOBAL_IP 
        self.port = GLOBAL_PORT 
        self.timeout = PIPELINE_TIMEOUT 
        self.msg_size = PIPELINE_MSGSIZE 
        self.remote_user = GLOBAL_USER
        self.remote_addr = GLOBAL_HOST
        self.logger = logger.getChild("director")

    def run(self):
        self.connect_to_daemon()
        self.job_thrd  = Process(target=Director.get_updates(self))
        self.data_thrd = Process(target=Director.get_datums(self))

    def connect_to_daemon(self):
        self.logger.info("Connecting to beanstalkd")
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except:
            self.logger.info("No daemon found, starting on %r", self.remote_addr)
            self.daemon = Popen("ssh {}@{} \"screen -dm beanstalkd -l {} -p {} -z {}\"".format(
                self.remote_user, self.remote_addr, self.ip, self.port, self.msg_size), shell=True)
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            time.sleep(1)
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        self.logger.info("Director ready")
        # we want to get updates from the webserver on the 'update' tube
        # and post the jobs on 'jobs' tube, receive on the 'results' and 'error' tube
        self.bsd.watch(TUBE_UPDATE)
        self.bsd.watch(TUBE_RESULTS)
        self.bsd.watch(TUBE_ERRORS)
        self.bsd.ignore("default")

        self.push_jobs({"kimid": "MO_607867530901_000", "priority": "normal"})

    def disconnect_from_daemon(self):
        self.bsd.close()
        self.daemon.kill()

    def get_tr_id(self):
        bsd  bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        bsd.watch(TUBE_TR_IDS)
        request = bsd.reserve()
        tr_id = request.body
        request.delete()
        bsd.close()
        return tr_id

    def get_updates(self):
        while 1:
            request = self.bsd.reserve()

            # got a request to update a model or test
            # from the website (or other trusted place)
            if request.stats()['tube'] == TUBE_UPDATE:
                # update the repository, try to compile the file
                # send it out as a job to compute
                #repo.rsync_update()
                self.push_jobs(simplejson.loads(request.body))

            # got word from a worker that a job is complete
            if request.stats()['tube'] == TUBE_RESULTS:
                ret = simplejson.loads(request.body)
                #repo.write_result_to_file(ret['result'])
                self.logger.info("Finished %r ...", ret['job'])
                self.logger.info("Results returned: %r", ret["result"])
                    
            if request.stats()['tube'] == TUBE_ERRORS:
                ret = simplejson.loads(request.body)
                self.logger.error("Errors occured: %r", ret['error'])

            request.delete()

    def priority_to_number(self,priority):
        priorities = {"immediate": 0, "very high": 0.01, "high": 0.1, 
                      "normal": 1, "low": 10, "very low": 100}
        if priority not in priorities.keys():
            priority = "normal"
        return priorities[priority]

    def push_jobs(self, update):
        self.bsd.use(TUBE_JOBS)
        kimid = update['kimid']
        priority_factor = self.priority_to_number(update['priority'])

        # is it a test that was updated or a model?
        if kimid in repo.KIM_TESTS:
            tests = [kimid]
            models = repo.models_for_test(kimid)
        elif kimid in repo.KIM_MODELS:
            models = [kimid]
            tests = repo.tests_for_model(kimid)
        else:
            self.logger.error("Tried to update invalid KIM ID!")

        for test in tests:
            for model in models: 
                priority = int(priority_factor*repo.test_model_to_priority(test,model) * 2**15)
                self.check_dependencies_and_push(test,model)

    def check_dependencies_and_push(self, test, model, child=None):
        test_dir = repo.test_dir(testname)
        # run the test in its own directory
        with repo.in_repo_dir(test_dir):
            #grab the input file
            with open(INPUT_FILE) as fl:
                ready, TRs, PAIRs = template.dependency_check(fl,model,test)

                self.logger.info("Submitting job <%s, %s> priority %i" % (test, model, priority))

                trid = self.get_tr_id()

                if not ready:
                    # Some test results are required
                    depids = []
                    for (t,m) in PAIRs:
                        self.logger.info("Submitting dependency <%s, %s>" % (t, m))
                        # FIXME - Maybe force higher priority?
                        depids.append(self.check_dependencies_and_push(t,m,child=(test,model,trid)))
                    # Delayed-put and bury, wait for dependencies to resolve FIXME
                    self.bsd.put(repr(Message(job=(test,model),jobid=trid, child=child, depends=TRs+tuple(depids))), priority=priority)
                else:
                    self.bsd.put(repr(Message(job=(test,model),jobid=trid, child=child, depends=TRs)), priority=priority)

    def halt(self):
        self.disconnect_from_daemon()


