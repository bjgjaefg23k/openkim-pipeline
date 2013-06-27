from config import *
import network
import rsync_tools
from logger import logging
logger = logging.getLogger("pipeline").getChild("gateway")

import simplejson, re, time, os, time
from mongodb import db, insert_one_result

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
        self.bean.watch(TUBE_WEB_UPDATES, TUBE_RESULTS)

    def process_messages(self):
        while 1:
            request = self.bean.reserve()
            tube = request.stats()['tube']
            if tube == TUBE_WEB_UPDATES:
                logger.debug("processing %r" % request.body)
                try:
                    if not PIPELINE_DEBUG:
                        rsync_tools.rsync_read_full(debug=self.debug)
                except Exception as e:
                    logger.error("%r" % e)
                self.bean.send_msg(TUBE_UPDATES, request.body)
            elif tube == TUBE_RESULTS:
                logger.debug("processing %r" % request.body)
                try:
                    if not PIPELINE_DEBUG:
                        rsync_tools.rsync_write_results(debug=self.debug)

                    kimcode = simplejson.loads(request.body)['jobid']
                    tries = ['tr', 'vr', 'er']
                    for leader in tries:
                        if os.path.exists(os.path.join(RSYNC_LOCAL_ROOT, leader, kimcode)):
                            insert_one_result(leader, kimcode)
                except Exception as e:
                    logger.error("%r" % e)
                self.bean.send_msg(TUBE_WEB_RESULTS, request.body)

            request.delete()

#==================================================
# storing and relaying messages from boxes
#==================================================
def s2d(s):
    return simplejson.loads(s)

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

def save_log(log):
    db.log.insert({"log": log})
    return log

def save_agent(uuid, obj):
    if not db.agent.find_one({"data.uuid": uuid}):
        db.agent.insert({"data.uuid": info})
    else:
        db.agent.update({"data.uuid": uuid}, {"$set": obj})
    agents[uuid] = obj

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
        self.sock_jobs.bind("tcp://127.0.0.1:%i" % GATEWAY_PORT_JOBS)

        self.sock_logs = self.con.socket(network.zmq.PUB)
        self.sock_logs.bind("tcp://127.0.0.1:%i" % GATEWAY_PORT_LOGS)

    def run(self):
        while 1:
            try:
                message = s2d(self.sock_rx.recv())
                # if it comes in on the 'logs' tube, send to the deque
                if message[0] == "logs":
                    templog = message[1]['message']
                    trimmed = save_log(templog)
                    self.sock_logs.send(trimmed)

                # if it is a reply to a request, treat it as
                # obj[1] is uuid | obj[2] is the message
                elif message[0] == "reply":
                    save_agent(message[1][0], message[1][1])

                # else treat like the job queue
                elif message[0] == "jobs":
                    dic = s2d(message[1])
                    trimmed = save_job(message[0], dic)
                    self.sock_jobs.send(simplejson.dumps({dic['jobid']: trimmed}))

            except Exception as e:
                raise


class Poller(network.Communicator):
    def __init__(self):
        super(Poller, self).__init__()

    def connect(self):
        super(Poller, self).connect()
        self.sock_rx.close()

    def run(self):
        while 1:
            self.sock_tx.send_pyobj(("ping","please"))
            time.sleep(2)

if __name__ == "__main__":
    import sys

    comm = WebCommunicator()
    comm.connect()
    comm.start()

    poll = Poller()
    poll.connect()
    poll.start()

    gate = Gateway()
    gate.connect_to_daemon()
    gate.process_messages()

