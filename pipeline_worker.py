import repository as repo
import beanstalkc as bean 
from subprocess import check_call, Popen, PIPE
from multiprocessing import Process
import runner
import urllib
import time
import simplejson
from config import *
from pipeline_global import *
logger = logger.getChild("pipeline")

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
                self.logger.info("Running %r ...", jobmsg.jobid)
                result = runner.run_test_on_model(*jobmsg.job)
                repo.write_result_to_file(result, jobmsg.jobid)
                
                #FIXME 
                #rsync.sync_directory()
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



