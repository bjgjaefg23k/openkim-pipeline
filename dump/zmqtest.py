#! /usr/bin/env python
from threading import Thread
import time, sys, zmq, uuid
import numpy as np

addr = "ipc://127.0.0.1:1999"
msg = np.random.rand(10000000)

class Comm(Thread):
    def __init__(self, data={}, sender=True):
        self.data = data
        self.sender = sender 

        super(Comm, self).__init__()
        self.daemon = True
        self.connect()

    def connect(self):
        self.con = zmq.Context()
        # open both the rx/tx lines, bound
        if self.sender == True:
            self.sock = self.con.socket(zmq.PAIR)
            self.sock.bind(addr)
        else: 
            self.sock = self.con.socket(zmq.PAIR)
            #self.sock.setsockopt(zmq.SUBSCRIBE, "")
            self.sock.connect(addr)

    def run(self):
        while 1:
            start = time.time()
            obj = np.frombuffer(self.sock.recv(copy=True))
            end = time.time()
            print "sum:",obj.sum()
            print "end:",end
            print end - start

    def send_msg(self, data):
        start = time.time()
        print "start:",start
        self.sock.send(data, copy=True)
        end = time.time()
        print "sum:",data.sum()
        print end - start

