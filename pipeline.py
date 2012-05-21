"""
Contains routines for running tests against models and vice versa
"""

import repository as repo
import beanstalkc as bean 
from subprocess import Popen, PIPE
from multiprocessing import Process
import urllib
import time
import simplejson

GLOBAL_PORT = 14177
TUBE_JOBS    = "jobs"
TUBE_RESULTS = "results"
TUBE_ERROR   = "error"
TUBE_UPDATE  = "update"

class Director(object):
    def __init__(self):
        self.ip = "127.0.0.1" 
        self.port = GLOBAL_PORT 
        self.timeout = 10

    def run(self):
        self.connect_to_daemon()
        self.job_thrd  = Process(target=Director.get_updates(self))
        self.data_thrd = Process(target=Director.get_datums(self))

    def connect_to_daemon(self):
        # connect to the daemon we created
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except:
            self.daemon = Popen("screen -dm beanstalkd -l {} -p {}".format(self.ip, self.port), shell=True)
            time.sleep(1)
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get updates from the webserver on the 'update' tube
        # and post the jobs on 'jobs' tube
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

            if request.stats()['tube'] == TUBE_UPDATE:
                push_jobs(request.body)
            if request.stats()['tube'] == TUBE_RESULTS:
                print request.body
            if request.stats()['tube'] == TUBE_ERROR:
                print request.body

            request.delete()

    def get_datums(self):
        pass

    def push_jobs(self, update):
        self.bsd.use(TUBE_JOBS)
        self.bsd.put(update)

    def halt(self):
        self.disconnect_from_daemon()


class Worker(object):
    def __init__(self):
        self.remote_user = "sethnagroup"
        self.remote_addr = "cerbo.ccmr.cornell.edu"
        self.ip = "127.0.0.1"
        self.timeout = 10
        self.port = GLOBAL_PORT

    def run(self):
        try:
            self.start_listen()
        except:
            self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
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

            jobtup = simplejson.loads(job.body)
            if len(jobtup) != 2:
                print "Bad job length, ", jobtup, ", removing..."
                job.delete()
                
                error = {"job": jobtup, "error": "length"}
                self.bsd.use(TUBE_ERROR)
                self.bsd.put(error)
            else:
                print "Running ", jobtup[0], "with", jobtup[1], "..."
                try:
                    result = run_test_on_model(*jobtup)
                    self.bsd.use(TUBE_RESULTS)
                    self.bsd.put(result)
                    job.delete()
                except Exception as e:
                    print "Run failed, removing..."
                    
                    error = {"job": jobtup, "error": e}
                    self.bsd.use(TUBE_ERROR)
                    self.bsd.put(error)
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
