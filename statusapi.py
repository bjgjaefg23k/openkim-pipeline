from config import *
from network import Communicator
from logger import logging, pygmentize
logger = logging.getLogger("pipeline").getChild("statusapi")

import simplejson, re, time, os
from collections import OrderedDict, deque
from os.path import join
from cStringIO import StringIO
import cPickle as pickle

from flask import make_response, Flask, request

import gevent
from gevent.pywsgi import WSGIServer
from gevent_zeromq import zmq
from geventwebsocket.handler import WebSocketHandler

#=================================================================
# The dictionary of jobs and how it is organized
#=================================================================
app = Flask(__name__)
app.debug = True
comm = None

regex = r"(?:([_a-zA-Z][_a-zA-Z0-9]*?)__)?([A-Z]{2})_([0-9]{10,12})(?:_([0-9]{3}))?"
agents = {}
jobs = OrderedDict()
logs = deque(maxlen=500)

comm = WebCommunicator()
comm.connect()

LOGSFILE = join(KIM_LOG_DIR, "pickle.logs")
JOBSFILE = join(KIM_LOG_DIR, "pickle.jobs")

def s2d(s):
    return simplejson.loads(s)

def d2s(d):
    return simplejson.dumps(d)

def get_leader(kimcode):
    name, leader, code, version = re.match(regex, kimcode).groups()
    return leader

def dic_insert(dic):
    jobs[dic["jobid"]] = dic

def dic_stash(tube, dic):
    # almost everything done with this loop - results and job are special
    # job needs to be split into test/model/verifier and results need to be 
    # re-jsoned
    tests  = ['jobid', 'priority', 'errors', 'message',
              'sitename', 'username', 'boxtype', 'ipaddr', 
              'vmversion', 'setuphash']
    info = {}
    for j in tests:
        if dic.has_key(j):
            info[j] = dic[j]
        else:
            info[j] = None
    info.update({"tube": tube})    
    
    # extract the test/model
    if dic.has_key('job'):
        first, second = dic['job']
        leader1 = get_leader(first)
        leader2 = get_leader(second)
        if leader1 == "VM" or leader1 == "VT":
            info.update({"verifier": first})       
        else:
            info.update({"test": first})       
        if leader2 == "TE":
            info.update({"test": second})
        else:
            info.update({"model": second})
    
    # re-json the results dictionary
    if dic.has_key('results'):
        info.update({"results": d2s(dic["results"])})

    # deal with running jobs 
    info["tube"] = tube
    if tube == "jobs":
        info["tube"] = "queued"
    dic_insert(info)
   
def arr_stash(log):
    logs.append(log)

def reply_stash(uuid, obj):
    agents[uuid] = obj 

def sync_to_disk(logfile, jobfile):
    while True:
        # sleep for a minute then write the logs
        gevent.sleep(60)
        with open(logfile, "w") as ff:
            pickle.dump(logs, ff, protocol=2)
        with open(jobfile, "w") as ff:
            pickle.dump(jobs, ff, protocol=2)

def load_from_disk(logfile, jobfile):
    global logs, jobs
    with open(logfile, "r") as ff:
        logs = pickle.load(ff)
    with open(jobfile, "r") as ff:
        jobs = pickle.load(ff)
      
#=================================================================
# Web interface to the information
#=================================================================
def trimjob(job):
    keys = ['jobid', 'tube', 'test', 'model']
    out = {}
    for key in keys:
        out.update({key: job[key]})
    return out

def pygment(string):
    st = StringIO()
    pygmentize(string, formatter="html", outfile=st)
    return st.getvalue() 

# this allows up to use two different processes to host the website
def loosen_security(msg):
    response = make_response(msg)
    response.headers['Access-Control-Allow-Origin'] = '*'
    return response

# this is the websocket that follows the progress of the beanstalkd tubes
@app.route(rule="/jobs")
def tube_handler():
    if request.environ.get("wsgi.websocket"):
        ws = request.environ['wsgi.websocket']
        sock = conn.con.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect('inproc://jobs')
        for key,val in jobs.iteritems():
            ws.send(simplejson.dumps({key:trimjob(val)}))
        while True:
            msg = sock.recv()
            ws.send(msg)
    return simplejson.dumps(jobs)
   
# the static method that requests certain error or result messages
# only one at a time.  not websocket based (get only) 
@app.route("/msg/<tube>/<tr>")
def msg_handler(tr=None, tube=None):
    output = d2s([j[tube] for j in jobs.values() if j['jobid'] == tr and j['tube'] == tube])
    return loosen_security(output)

# the websocket method to follow the tail of the combined logs 
@app.route("/logs")
def logs_handler():
    if request.environ.get("wsgi.websocket"):
        ws = request.environ['wsgi.websocket']
        sock = conn.con.socket(zmq.SUB)
        sock.setsockopt(zmq.SUBSCRIBE, "")
        sock.connect('inproc://logs')
        for log in logs:
            ws.send(pygment(log))
        while True:
            msg = sock.recv()
            ws.send(pygment(msg))
    return pygment("\n".join([l for l in logs]))

@app.route("/agents/", defaults={'uuid': None})
@app.route("/agents/<uuid>")
def agents_uuids(uuid=None):
    if uuid is None:
        output = d2s(agents.keys())
    else:
        if agents.has_key(uuid):
            output = d2s(agents[uuid])
        else:
            output = ''
    return loosen_security(output)

#==================================================================
# communicator which gathers the information and sends out requests
#==================================================================
class WebCommunicator(Communicator):
    def __init__(self):
        # api request specific objects
        self.info = {}
        super(WebCommunicator, self).__init__()

    def connect(self):
        super(WebCommunicator, self).connect()

        # in process sockets to send data to the websockets
        self.sock_jobs = self.con.socket(zmq.PUB)
        self.sock_jobs.bind("inproc://jobs")

        self.sock_logs = self.con.socket(zmq.PUB)
        self.sock_logs.bind("inproc://logs")

    def run(self):
        while 1:
            try:
                message = s2d(self.sock_rx.recv())
                # if it comes in on the 'logs' tube, send to the deque
                if message[0] == "logs":
                    templog = message[1]['message']
                    arr_stash(templog)
                    self.sock_logs.send(templog)

                # if it is a reply to a request, treat it as 
                # obj[1] is uuid | obj[2] is the message
                elif message[0] == "reply":
                    reply_stash(message[1][0], message[1][1])

                # else treat like the job queue
                else:
                    dic = s2d(message[1])
                    dic_stash(message[0], dic)
                    self.sock_jobs.send(simplejson.dumps({dic['jobid']: trimjob(jobs[dic['jobid']])}))

            except Exception as e:
                raise 

    def poll_uuid(self):
        while 1:
            global agents
            agents = {}
            self.sock_tx.send_pyobj(("ping","please"))
            gevent.sleep(2)

#================================================================
# of course, the main
#================================================================
if __name__ == "__main__":
    import sys
    port = 8080

    if PIPELINE_DEBUG:
        LOGSFILE = LOGSFILE+".dbg"
        JOBSFILE = JOBSFILE+".dbg"
        port = 8081

    http_server = WSGIServer(('',port), app, handler_class=WebSocketHandler)

    try:
        load_from_disk(LOGSFILE, JOBSFILE)
    except Exception as e:
        print "Could not open pickled status, restarting..."

    gevent.spawn(sync_to_disk, LOGSFILE, JOBSFILE)
    gevent.spawn(WebCommunicator.run, comm)
    gevent.spawn(WebCommunicator.poll_uuid, comm)
    http_server.serve_forever()

