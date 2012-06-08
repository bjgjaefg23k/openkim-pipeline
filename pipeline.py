from config import *
from pipeline_director import Director 
from pipeline_worker import Worker
from pipeline_website import Site

if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-w", "--worker", dest="worker", action="store_true", 
                                      help="indicates to run as a worker")
    parser.add_option("-d", "--director", dest="director", action="store_true", 
                                      help="indicates to run as the director")
    parser.add_option("-s", "--site", dest="site", action="store_true", 
                                      help="indicates to run as the fake website")
    (options, args) = parser.parse_args()
    worker = options.worker
    director = options.director
    site = options.site

    if director == True:
        obj = Director()
        obj.run()
    elif worker == True:
        obj = Worker()
        obj.run()
    elif site == True:
        obj = Site()
        obj.run()
    else:
        parser.print_help() 
