import beanstalkc as bean 
from subprocess import check_call, Popen, PIPE
from multiprocessing import Process
import runner
import urllib
import time
import simplejson
import rsync_tools
from config import *
from pipeline_global import *
logger = logger.getChild("pipeline")
import models

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
            self.logger.info("Waiting to connect to beanstalkd")
            time.sleep(PIPELINE_WAIT)
            self.start_listen()

        self.logger.info("Connected to daemon")
        self.get_jobs()

    def start_listen(self):
        # connect to the daemon we created
        self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get jobs from the 'jobs' tube 
        self.bsd.watch(TUBE_JOBS)
        self.bsd.ignore("default")
        
    def get_jobs(self):
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



