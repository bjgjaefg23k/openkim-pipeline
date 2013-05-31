import beanstalkc as bean
from subprocess import check_call, Popen, PIPE
import subprocess, tempfile
import simplejson
import sqlite3 as lite
import re

RSYNC_PATH          = "pipeline@openkim.org:/"
RSYNC_LOG_FILE_FLAG = "--log-file=rsynclog/rsync.log"
LOCAL_REPO_ROOT     = "/repository/"
LOCAL_REPO_ROOT_DBG = "/repository_dbg/"
RSYNC_FLAGS         = "-rtpgoDOL -uzRhEc --progress --stats -e 'ssh -i /home/ubuntu/id_ecdsa_pipeline \
                     -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no' --exclude-from=/home/ubuntu/gateway/rsync-exclude"

def rsync_command(files,read=True,path=None,debug=False,tr_fix=False):
    path = path or RSYNC_PATH
    if debug == False:
        local_repo = LOCAL_REPO_ROOT
    else:
        local_repo = LOCAL_REPO_ROOT_DBG

    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.file.write("\n".join(files))
        tmp.file.close()
        flags = RSYNC_FLAGS
        try:
            print "rsyncing", files
            if read == True:
                if tr_fix == True:
                    flags = "-f \"- */tr\" " + flags
                flags = " --delete " + flags
                cmd = " ".join(["rsync",flags,path,RSYNC_LOG_FILE_FLAG,"--files-from={}".format(tmp.name),local_repo])
            else:
                cmd = " ".join(["rsync",flags,RSYNC_LOG_FILE_FLAG,"--files-from={}".format(tmp.name),local_repo,path])
            subprocess.check_call(cmd, shell=True)
        except subprocess.CalledProcessError:
            raise

def rsync_read_full(debug=False):
    # first, read everything from the /read directory, except all mentions of tr/
    rsync_command(["read/submitted/", "read/approved/"], read=True, debug=debug, tr_fix=True)
    
    # depending on debug, take in the results as well
    if debug == True:
        rsync_command(["write/debug/"], read=True, debug=debug)
    else:
        rsync_command(["write/results/"], read=True, debug=debug)

def rsync_write_results(debug=False):
    # write the results back to the webserver in the appropriate place
    if debug == True:
        rsync_command(["write/debug/tr/", "write/debug/vr/"], read=False, debug=debug)
    else:
        rsync_command(["write/results/tr/", "write/results/vr/"], read=False, debug=debug)

TUBE_WEB_UPDATES = "web_updates"
TUBE_WEB_RESULTS = "web_results"
TUBE_UPDATES     = "updates"
TUBE_RESULTS     = "results"

class Gateway(object):
    def __init__(self, debug=False):
        self.ip      = "127.0.0.1"
        self.port    = 14177
        self.timeout = 30
        if debug == True:
            self.port = 14174
        self.debug = debug

    def post_msg(self, tube, msg):
        self.bsd.use(tube)
        self.bsd.put(msg)

    def connect_to_daemon(self):
        try:
            self.bsd = bean.Connection(host=self.ip, port=self.port, connect_timeout=self.timeout)
        except Exception as e:
            print "We could not connect, please start the daemon first"

        self.bsd.watch(TUBE_WEB_UPDATES)
        self.bsd.watch(TUBE_RESULTS)
        self.bsd.ignore("default")

    def process_messages(self):
        while 1:
            request = self.bsd.reserve()
            tube = request.stats()['tube']
            if tube == TUBE_WEB_UPDATES:
                try:
                    if self.debug == False:
                        rsync_read_full(debug=self.debug)
                except Exception as e:
                    print e
                self.post_msg(TUBE_UPDATES, request.body)
            elif tube == TUBE_RESULTS:
                try:
                    if self.debug == False:
                        rsync_write_results(debug=self.debug)
                except Exception as e:
                    print e
                self.post_msg(TUBE_WEB_RESULTS, request.body)

            request.delete()


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        gate = Gateway(debug=True)
        print "DEBUG MODE : ON"
    else:
        gate = Gateway(debug=False)

    gate.connect_to_daemon()
    gate.process_messages()

