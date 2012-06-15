#!/usr/bin/env python
from config import *
from pipeline_director import Director 
from pipeline_worker import Worker
from pipeline_website import Site

if __name__ == "__main__":
    import sys
    if len(sys.argv) == 2:
        if sys.argv[1] == "director":
            obj = Director()
            obj.run()
        elif sys.argv[1] == "worker":
            obj = Worker()
            obj.run()
        elif sys.argv[1] == "site":
            obj = Site()
            obj.run()
            obj.send_update("MO_607867530901_000")
    else:
        print "Specify {worker|director|site}"
        exit(1)
