"""
Message format for the queue system:
    "jobid":    id assigned from the director 
    "priority": a string priority
    "job":      an array of tuples of (testid, modelid, testresult id)
    "results":  the json message produced by the run
    "errors":   the exception caught and returned as a string
"""
KEY_JOBID    = "jobid"
KEY_PRIORITY = "priority"
KEY_JOB      = "job"
KEY_RESULTS  = "results"
KEY_ERRORS   = "errors"
KEY_DEPENDS  = "depends"

def Message(object):
    def __init__(self, string=None, jobid=None, priority=None, job=None, results=None, errors=None, depends=None):
        if string is not None:
            self.msg_from_string(string)
        else:
            self.jobid = jobid
            self.priority = priority
            self.job = job
            self.results = results
            self.errors = errors
            self.depends = depends

    def __repr__(self):
        return simplejson.dumps({KEY_JOBID: self.jobid, KEY_PRIORITY: self.priority,
            KEY_JOB: self.job, KEY_RESULTS: self.results, KEY_ERRORS: self.errors, KEY_DEPENDS: self.depends})

    def msg_from_string(self,string):
        dic = simplejson.loads(string)
        self.jobid = dic[KEY_JOBID]
        self.priority = dic[KEY_PRIORITY]
        self.job = dic[KEY_JOB]
        self.results = dic[KEY_RESULTS]
        self.errors = dic[KEY_ERRORS]
        self.depends = dic[KEY_DEPENDS]
