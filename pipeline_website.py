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
import kimid
logger = logger.getChild("pipeline")

class Site(object):
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
            self.bsd.put(kimid.new_kimid("TR"))


    def send_update(self, kimid):
        self.bsd.use(TUBE_UPDATE)
        self.bsd.put(simplejson.dumps({"kimid": kimid, "priority":"normal"}))


