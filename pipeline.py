import repository as repo
import beanstalkc as bean 
from subprocess import check_call, Popen, PIPE
from multiprocessing import Process
import runner
import urllib
import time
import simplejson
from config import *
logger = logger.getChild("pipeline")

TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_ERROR   = "errors"
TUBE_UPDATE  = "updates"

class Director(object):
    def __init__(self):
        self.ip   = GLOBAL_IP 
        self.port = GLOBAL_PORT 
        self.timeout = 10
        self.msg_size = 2**16
        self.remote_user = GLOBAL_USER
        self.remote_addr = GLOBAL_HOST
        logger = logger.getChild("director")

    def run(self):
        self.connect_to_daemon()
        self.job_thrd  = Process(target=Director.get_updates(self))
        self.data_thrd = Process(target=Director.get_datums(self))

    def connect_to_daemon(self):
        print "Connecting to beanstalkd"
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except:
            print "No daemon found, starting on", self.remote_addr
            self.daemon = Popen("ssh {}@{} \"screen -dm beanstalkd -l {} -p {} -z {}\"".format(
                self.remote_user, self.remote_addr, self.ip, self.port, self.msg_size), shell=True)
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            time.sleep(1)
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        print "Director ready"
        # we want to get updates from the webserver on the 'update' tube
        # and post the jobs on 'jobs' tube, receive on the 'results' and 'error' tube
        self.bsd.watch(TUBE_UPDATE)
        self.bsd.watch(TUBE_RESULTS)
        self.bsd.watch(TUBE_ERROR)
        self.bsd.ignore("default")

    def disconnect_from_daemon(self):
        self.bsd.close()
        self.daemon.kill()

    def get_updates(self):
        while 1:
            request = self.bsd.reserve()
            request.bury()

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
                repo.write_result_to_file(ret['result'])
                print "Finished", ret['job'], "..."

            # got word from a worker that a job errored out
            if request.stats()['tube'] == TUBE_ERROR:
                ret = simplejson.loads(request.body)
                print "Error on job", ret['job'], " = ", ret["error"]

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
            for model in repo.models_for_test(kimid):
                priority = int(priority_factor*repo.test_model_to_priority(kimid,model) * 2**15)
                print "Submitting job <%s, %s> priority %i" % (kimid, model, priority)
                self.bsd.put(simplejson.dumps([kimid,model]), priority=priority)
        elif kimid in repo.KIM_MODELS:
            for test in repo.tests_for_model(kimid):
                priority = int(priority_factor*repo.test_model_to_priority(kimid,model) * 2**15)
                print "Submitting job <%s, %s> priority %i" % (kimid, model, priority)
                self.bsd.put(simplejson.dumps([test,kimid]))
        else:
            print "Tried to update invalid KIM ID!"

    def halt(self):
        self.disconnect_from_daemon()


class Worker(object):
    def __init__(self):
        self.remote_user = GLOBAL_USER 
        self.remote_addr = GLOBAL_HOST 
        self.ip          = GLOBAL_IP 
        self.timeout = 10
        self.port = GLOBAL_PORT
        logger = logger.getChild("worker")

    def run(self):
        # if we can't already connect to the daemon on localhost,
        # open an ssh tunnel to the daemon and start the beanstalk
        try:
            self.start_listen()
        except:
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(
                self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
            time.sleep(1)
            self.start_listen()

        print "Connected to director"
        self.get_jobs()

    def start_listen(self):
        # connect to the daemon we created
        self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get jobs from the 'jobs' tube 
        self.bsd.watch(TUBE_JOBS)
        self.bsd.ignore("default")
        
    def get_jobs(self):
        while 1:
            job = self.bsd.reserve()
            job.bury()

            # got a job -----
            # update the repository, attempt to run the job
            # and return the results to the director
            #repo.rsync_update()
            jobtup = simplejson.loads(job.body)
            try:
                print "Running ", jobtup, "..."
                result = runner.run_test_on_model(*jobtup)
                result = {"job": jobtup, "result": result}
                self.bsd.use(TUBE_RESULTS)
                self.bsd.put(simplejson.dumps(result))
                job.delete()
            
            except Exception as e:
                print "Run failed, removing..."
                error = {"job": jobtup, "error": str(e)}
                self.bsd.use(TUBE_ERROR)
                self.bsd.put(simplejson.dumps(error))
                job.delete()



if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-w", "--worker", dest="worker", action="store_true", 
                                      help="indicates to run as a worker")
    parser.add_option("-d", "--director", dest="director", action="store_true", 
                                      help="indicates to run as the director")
    (options, args) = parser.parse_args()
    worker = options.worker
    director = options.director

    if director == True:
        obj = Director()
        obj.run()
    elif worker == True:
        obj = Worker()
        obj.run()
    else:
        parser.print_help() 
