"""
Contains routines for running tests against models and vice versa
"""

import time
import repository as repo
from subprocess import Popen, PIPE
import urllib
import beanstalkc as bean 
import simplejson

GLOBAL_PORT = 14177

class Director(object):
    def __init__(self):
        self.ip = "127.0.0.1" 
        self.port = GLOBAL_PORT 
        self.timeout = 10

    def run(self):
        self.start_daemon()
        self.connect_to_daemon()
        self.get_updates()

    def start_deamon(self):
        # FIXME - error checking on open
        self.daemon = Popen("beanstalkd -l {} -p {} -d".format(self.ip, self.host), shell=True)

    def stop_daemon(self):
        self.daemon.kill()

    def connect_to_daemon(self):
        # connect to the daemon we created
        self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get updates from the webserver on the 'update' tube
        # and post the jobs on 'jobs' tube
        self.watch("updates")
        self.use("jobs")

    def get_updates(self):
        while 1:
            update = self.bsd.reserve()
            push_jobs(update.body)

    def push_jobs(self, update):
        self.bsd.put(update)


class Worker(object):
    def __init__(self):
        self.remote_user = "sethnagroup"
        self.remote_addr = "cerbo.ccmr.cornell.edu"
        self.ip = "127.0.0.1"
        self.timeout = 10
        self.port = GLOBAL_PORT

    def run(self):
        self.ssh = Popen("screen -dm ssh -L{}:{}:{} {}@{}".format(self.port,self.ip,self.port,self.remote_user,self.remote_addr), shell=True)
        time.sleep(5)
        self.start_listen()

    def start_listen(self):
        # connect to the daemon we created
        self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)

        # we want to get jobs from the 'jobs' tube 
        self.watch("jobs")

        while 1:
            job = self.bsd.reserve()
            run_test_on_model(*job.body.split("\n"))

    def run_test_on_model(testname,modelname):
        """ run a test with the corresponding model, capture the output as a dict """
        if testname not in repo.KIM_TESTS:
            raise KeyError, "test <{}> not valid".format(testname)
        if modelname not in repo.KIM_MODELS:
            raise KeyError, "model <{}> not valid".format(modelname)

        executable = repo.test_executable(testname)
        process = Popen(executable,stdin=PIPE,stdout=PIPE)
        stdout, stderr = process.communicate(modelname)

        if process.poll() is None:
            process.kill()
            raise RuntimeError, "your test didn't terminate nicely"

        data_string = stdout.splitlines()[-1]
        return simplejson.loads(data_string)


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
