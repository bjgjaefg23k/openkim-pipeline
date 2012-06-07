import repository as repo
import beanstalkc as bean 
from subprocess import check_call, Popen, PIPE
from multiprocessing import Process
import runner
import urllib
import time
import simplejson
from config import *
from pipeline import *
logger = logger.getChild("pipeline")

PIPELINE_TIMEOUT = 10
PIPELINE_MSGSIZE = 2**20
TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_UPDATE  = "updates"
TUBE_ERRORS  = "errors"

class Worker(object):
    def __init__(self):
        self.remote_user = GLOBAL_USER 
        self.remote_addr = GLOBAL_HOST 
        self.ip          = GLOBAL_IP 
        self.timeout = PIPELINE_TIMEOUT 
        self.port = GLOBAL_PORT
        self.logger = logger.getChild("worker")

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

        self.logger.info("Connected to director")
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
                self.logger.info("Running %r ...", jobtup)
                result = runner.run_test_on_model(*jobtup)
                result = {"job": jobtup, "result": result}
                self.bsd.use(TUBE_RESULTS)
                self.bsd.put(simplejson.dumps(result))
                job.delete()
            
            except Exception as e:
                self.logger.error("Run failed, removing...")
                error = {"job": jobtup, "error": str(e)}
                self.bsd.use(TUBE_RESULTS)
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
