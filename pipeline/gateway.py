import json
import re
import time

from threading import Thread
from datetime import datetime
from bson.json_util import dumps

import network
import database
import rsync_tools
from mongodb import db, insert_one_result, insert_one_object

import config as cf
from logger import logging
logger = logging.getLogger("pipeline").getChild("gateway")

regex = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{10,12})(?:_([0-9]{3}))?"
RSYNC_FLAGS = "-rtpgoDOL -uzRhEc --progress --stats"

#===================================================
# handling messages that come off the beanstalkd
#===================================================
class Gateway(object):
    def __init__(self):
        self.bean = network.BeanstalkConnection()

    def connect_to_daemon(self):
        self.bean.connect()
        self.bean.watch(cf.TUBE_WEB_UPDATES, cf.TUBE_RESULTS, cf.TUBE_ERRORS)

    def process_messages(self):
        while 1:
            request = self.bean.reserve()
            tube = request.stats()['tube']
            if tube == cf.TUBE_WEB_UPDATES:
                logger.debug("processing %r" % request.body)
                try:
                    job = json.loads(request.body)
                    approved = True if job['status'] == 'approved' else False
                    rsync_tools.gateway_full_read()

                    kimcode = job['kimid']
                    if database.isuuid(kimcode):
                        leader = database.uuid_type(kimcode)
                        insert_one_result(leader, kimcode)
                    else:
                        insert_one_object(kimcode)
                    self.bean.send_msg(cf.TUBE_UPDATES, request.body)
                except Exception as e:
                    logger.error("%r" % e)
            elif tube == cf.TUBE_RESULTS or tube == cf.TUBE_ERRORS:
                logger.debug("processing %r" % request.body)
                try:
                    kimcode = json.loads(request.body)['jobid']
                    leader = database.uuid_type(kimcode)
                    if database.isuuid(kimcode):
                        leader = database.uuid_type(kimcode)
                        insert_one_result(leader, kimcode)
                    rsync_tools.gateway_write_result(leader, kimcode)
                    rsync_tools.ssh_touch_done(leader, kimcode)

                    if tube == cf.TUBE_RESULTS:
                        self.bean.send_msg("web_updates", json.dumps({"kimid": kimcode, "priority": "normal", "status": "approved"}))

                except Exception as e:
                    logger.error("%r" % e)
                self.bean.send_msg(cf.TUBE_WEB_RESULTS, request.body)

            request.delete()

#==================================================
# storing and relaying messages from boxes
#==================================================
def s2d(s):
    return json.loads(s)

def get_leader(kimcode):
    name, leader, code, version = re.match(regex, kimcode).groups()
    return leader

def save_job(tube, dic):
    tests  = ['jobid', 'priority', 'errors', 'message',
              'sitename', 'username', 'boxtype', 'ipaddr',
              'vmversion', 'setuphash']
    info = {}
    for j in tests:
        info[j] = dic.get(j, None)
    info.update({"tube": tube})

    # extract the test/model
    if dic.has_key('job'):
        first, second = dic['job']
        info.update({"test": first})
        info.update({"model": second})

    # re-json the results dictionary
    if dic.has_key('results'):
        info.update({"results": dic["results"]})
    if tube == "jobs":
        info["tube"] = "queued"

    # actually store in the database    
    if not db.job.find_one({"jobid": dic['jobid']}):
        db.job.insert(info)
    else:
        db.job.update({"jobid": dic['jobid']}, {"$set": info})
    return trimjob(info)

def save_log(full):
    log = full.get('message', None)
    uuid = full.get('uuid', None)
    cid = full.get('cid', None)

    trimmed = {"log": log, 'uuid': uuid, 'cid': cid, 'date': str(datetime.utcnow())}
    db.log.insert(trimmed)
    trimmed.pop('_id')
    return trimmed

def save_agent(uuid, obj):
    if not db.agent.find_one({"uuid": uuid}):
        db.agent.insert(obj)
    else:
        db.agent.update({"uuid": uuid}, {"$set": obj})

def trimjob(job):
    keys = ['jobid', 'tube', 'test', 'model']
    out = {}
    for key in keys:
        out.update({key: job[key]})
    return out

#==================================================================
# communicator which gathers the information and sends out requests
#==================================================================
class WebCommunicator(network.Communicator):
    def __init__(self):
        # api request specific objects
        self.info = {}
        super(WebCommunicator, self).__init__()

    def connect(self):
        super(WebCommunicator, self).connect()

        # in process sockets to send data to the websockets
        self.sock_jobs = self.con.socket(network.zmq.PUB)
        self.sock_jobs.bind("tcp://127.0.0.1:%i" % cf.GATEWAY_PORT_JOBS)

        self.sock_logs = self.con.socket(network.zmq.PUB)
        self.sock_logs.bind("tcp://127.0.0.1:%i" % cf.GATEWAY_PORT_LOGS)

    def run(self):
        while 1:
            try:
                message = s2d(self.sock_rx.recv())

                # if it comes in on the 'logs' tube, send to the deque
                if message[0] == "logs":
                    trimmed = save_log(message[1])
                    self.sock_logs.send(dumps(trimmed))

                # if it is a reply to a request, treat it as
                # obj[1] is uuid | obj[2] is the message
                elif message[0] == "reply":
                    uuid = message[1][0]
                    modified = message[1][1]
                    modified.update({"uuid": uuid})
                    save_agent(uuid, modified)

                # else treat like the job queue
                else:
                    dic = s2d(message[1])
                    trimmed = save_job(message[0], dic)
                    self.sock_jobs.send(json.dumps({dic['jobid']: trimmed}))

            except Exception as e:
                raise


class Poller(Thread):
    def __init__(self, sock_tx):
        super(Poller, self).__init__()
        self.daemon = True
        self.sock_tx = sock_tx

    def run(self):
        while 1:
            self.sock_tx.send_pyobj(("ping","please"))
            time.sleep(2)

if __name__ == "__main__":
    import sys

    logger.info("Starting communicator")
    comm = WebCommunicator()
    comm.connect()
    comm.start()

    logger.info("Starting polling thread")
    poll = Poller(comm.sock_tx)
    poll.start()

    gate = Gateway()
    gate.connect_to_daemon()
    gate.process_messages()

