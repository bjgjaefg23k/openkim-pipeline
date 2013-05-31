"""
network.py is the section of the pipeline that handles the network
communication between directors, workers, and webiste through
the beanstalk daemon. 

Any of the classes below rely on a secure public key to open an ssh
tunnel to the remote host.  It then connects to the beanstalkd
across this tunnel.
"""
import beanstalkc as bean
import time, simplejson, zmq
from threading import Thread

from config import *
from logger import logging, log_formatter
logger = logging.getLogger("pipeline").getChild("network")

def open_ports(port=BEAN_PORT, rx=PORT_RX, tx=PORT_TX, user=GLOBAL_USER, 
        addr=GLOBAL_HOST, ip=GLOBAL_IP):
    try:
        bsd = bean.Connection(ip, port, GLOBAL_TOUT)
        bsd.close()
    except bean.SocketError:
        st  = ""
        st += "screen -dm ssh -i /persistent/id_rsa -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no "  
        st +=                 "-L{}:{}:{}   -L{}:{}:{}  -L{}:{}:{}  {}@{}"
        ssh = Popen(st.format(port,ip,port,  rx,ip,rx,  tx,ip,tx,   user,addr), shell=True)
        logger.info("Waiting to open ports via ssh tunnels")
        time.sleep(1)

#==================================================================
# communicator which gathers the information and sends out requests
#==================================================================
class Communicator(Thread):
    def __init__(self):
        # decide on the port order
        self.port_tx = PORT_TX
        self.port_rx = PORT_RX 
 
        super(Communicator, self).__init__()
        self.daemon = True
        self.handler_funcs = []
        self.handler_args  = []

    def connect(self):
        self.con = zmq.Context()
        # open both the rx/tx lines, bound
        self.sock_tx = self.con.socket(zmq.PUB)
        self.sock_tx.connect("tcp://127.0.0.1:"+str(self.port_tx))
 
        self.sock_rx = self.con.socket(zmq.SUB)
        self.sock_rx.setsockopt(zmq.SUBSCRIBE, "")
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
        self.sock_tx.send(simplejson.dumps([tube, msg]))


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
        self.comm.send_msg(TUBE_LOGS,message)

def addNetworkHandler(comm, boxinfo):
    # add in the beanstalk logger if applicable
    network_handler = NetworkHandler(comm, boxinfo)
    network_handler.setLevel(logging.INFO)
    network_handler.setFormatter(log_formatter)
    logger.addHandler(network_handler)

