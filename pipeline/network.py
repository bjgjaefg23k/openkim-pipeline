"""
network.py is the section of the pipeline that handles the network
communication between directors, workers, and webiste through
the beanstalk daemon. 

Any of the classes below rely on a secure public key to open an ssh
tunnel to the remote host.  It then connects to the beanstalkd
across this tunnel.
"""
import zmq
import time
import json
import beanstalkc as bean
from subprocess import Popen
from threading import Thread

import config as cf
from logger import logging, log_formatter
logger = logging.getLogger("pipeline").getChild("network")

# TODO: switch this over to provy / fabric framework 
# ssh -f (run in the background) -N (only port forwarding) pipeline
# and using .ssh/config

def open_ports(port=cf.BEAN_PORT, rx=cf.PORT_RX, tx=cf.PORT_TX, user=cf.GLOBAL_USER, 
        addr=cf.GLOBAL_HOST, ip=cf.GLOBAL_IP):
    try:
        bsd = bean.Connection(ip, port, cf.GLOBAL_TOUT)
        bsd.close()
    except bean.SocketError:
        st  = ""
        st += "screen -dm ssh -i {} -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "  
        st +=                 "-L{}:{}:{}   -L{}:{}:{}  -L{}:{}:{}  {}@{}"
        ssh = Popen(st.format(cf.GLOBAL_KEY, port,ip,port,  
                rx,ip,rx,  tx,ip,tx,   user,addr), shell=True)
        logger.info("Waiting to open ports via ssh tunnels")
        time.sleep(1)

#==================================================================
# a generic beanstalk connection
#==================================================================
class BeanstalkConnection(object):
    def __init__(self, ):
        self.ip       = cf.GLOBAL_IP
        self.port     = cf.BEAN_PORT
        self.timeout  = cf.PIPELINE_TIMEOUT
        self.msg_size = cf.PIPELINE_MSGSIZE

    def connect(self):
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except bean.SocketError:
            # We failed to connect, this is really bad
            logger.error("Failed to connect to beanstalk queue after launching ssh")
            raise bean.SocketError("Failed to connect to %s" % cf.GLOBAL_HOST)
 
    def disconnect(self):
        if self.bsd:
            self.bsd.close()

    def send_msg(self, tube, msg):
        self.bsd.use(tube)
        self.bsd.put(msg)

    def watch(self, *tubes):
        for tube in tubes:
            self.bsd.watch(tube)

    def reserve(self):
        return self.bsd.reserve()


#==================================================================
# communicator which gathers the information and sends out requests
#==================================================================
class Communicator(Thread):
    def __init__(self):
        self.con = zmq.Context()

        # decide on the port order
        self.port_tx = cf.PORT_TX
        self.port_rx = cf.PORT_RX 
 
        super(Communicator, self).__init__()
        self.daemon = True
        self.handler_funcs = []
        self.handler_args  = []

    def connect(self):
        # open both the rx/tx lines, bound
        self.sock_tx = self.con.socket(zmq.PUB)
        self.sock_rx = self.con.socket(zmq.SUB)
        self.sock_rx.setsockopt(zmq.SUBSCRIBE, "")
        if cf.PIPELINE_GATEWAY:
            try:
                self.sock_tx.bind("tcp://127.0.0.1:"+str(self.port_tx))
                self.sock_rx.bind("tcp://127.0.0.1:"+str(self.port_rx))
            except zmq.ZMQError:
                logger.info("Address is already bound, switching to connect...")
                # we are already bound to the address, so just connect
                self.sock_tx.connect("tcp://127.0.0.1:"+str(self.port_tx))
                self.sock_rx.connect("tcp://127.0.0.1:"+str(self.port_rx))
        else:
            self.sock_tx.connect("tcp://127.0.0.1:"+str(self.port_tx))
            self.sock_rx.connect("tcp://127.0.0.1:"+str(self.port_rx))

    def addHandler(self, func, args):
        self.handler_funcs.append(func)
        self.handler_args.append(args)

    def disconnect(self):
        pass

    def run(self):
        while 1:
            try:
                obj = self.sock_rx.recv_pyobj()
                header, message = obj

                for func, args in zip(self.handler_funcs, self.handler_args):
                    func(header, message, *args)

            except Exception as e:
                # just let it go, you failed.
                logger.error("comm had an error: %r" % e)
                pass

    def send_msg(self, tube, msg):
        self.sock_tx.send(json.dumps([tube, msg]))


#==================================================================
# network logging handler
#==================================================================
class NetworkHandler(logging.Handler):
    """ A beanstalk logging handler """
    def __init__(self,communicator, boxinfo):
        self.comm = communicator
        self.info = boxinfo
        super(NetworkHandler,self).__init__()

    def emit(self,record):
        """ Send the message """
        err_message = self.format(record)
        message = self.info.copy()
        message['message'] = err_message
        #self.comm.send_msg(cf.TUBE_LOGS,message)

def addNetworkHandler(comm, boxinfo):
    # add in the beanstalk logger if applicable
    from logger import logging
    tlog = logging.getLogger("pipeline")

    network_handler = NetworkHandler(comm, boxinfo)
    network_handler.setLevel(logging.INFO)
    network_handler.setFormatter(log_formatter)
    tlog.addHandler(network_handler)

class Message(dict):
    def __init__(self, **kwargs):
        super(Message, self).__init__()
        dic = kwargs
        if kwargs.has_key('string'):
            dic = json.loads(kwargs['string'])
        for key in dic.keys():
            self[key] = dic[key]

    def __getattr__(self, name):
        if not self.has_key(name):
            return None
        return self[name]

    def __setattr__(self, name, value):
        self[name] = value

    def __repr__(self):
        return json.dumps(self)
