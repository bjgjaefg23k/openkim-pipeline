from config import *
import network
import rsync_tools

RSYNC_FLAGS = "-rtpgoDOL -uzRhEc --progress --stats"

class Gateway(object):
    def __init__(self, debug=False):
        self.debug = debug
        self.bean = network.BeanstalkConnection()

    def connect_to_daemon(self):
        self.bean.connect()
        self.bean.watch(TUBE_WEB_UPDATES, TUBE_RESULTS)

    def process_messages(self):
        while 1:
            request = self.bean.reserve()
            tube = request.stats()['tube']
            if tube == TUBE_WEB_UPDATES:
                try:
                    if not self.debug:
                        rsync_read_full(debug=self.debug)
                except Exception as e:
                    print e
                self.post_msg(TUBE_UPDATES, request.body)
            elif tube == TUBE_RESULTS:
                try:
                    if not self.debug:
                        rsync_write_results(debug=self.debug)
                except Exception as e:
                    print e
                self.post_msg(TUBE_WEB_RESULTS, request.body)

            request.delete()


if __name__ == "__main__":
    import sys

    gate = Gateway(debug=debug)
    gate.connect_to_daemon()
    gate.process_messages()

