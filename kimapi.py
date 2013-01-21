""" Contains some wrapped KIM_API calls,

    going through kimservice
"""

import os, sys, re
import kimservice
from config import *
logger = logger.getChild("repository")

#match_args   = re.compile(r"^(\(\?.*\?\))?([a-zA-Z0-9_\-]*)?(\/*.*)")
match_slash  = re.compile(r"^(\/)*(.*)")
match_filter = re.compile(r"^\(\?(.*?)\?\)(\/*.*)")
match_object = re.compile(r"^([a-zA-Z0-9_\-:]*)(\/*.*)")

match_comment = r"(@#.*?#@)"
match_replace = r"@@(.*?)@@"
match_index   = r"@\[(\d)\]@"

#=======================================================
# the base APIObject which implements all standard calls
#=======================================================
class APIObject(object):
    def _special_calls(self, arg0):
        pass

    def _break_into_parts(self, query):
        query = match_slash.match(query).groups()[1]
        
        grp_flt = match_filter.match(query)
        grp_obj = match_object.match(query)

        obj = fltr = None
        if grp_flt:
            fltr, args = grp_flt.groups()
        else:
            obj, args = grp_obj.groups()
        return (fltr, obj, args)

    def _filter(self, fltr):
        fltr = re.sub(match_comment, r"", fltr)
        fltr = re.sub(match_replace, r"self.api('\1')", fltr)
        return eval(fltr)

    def _call(self, obj):
        return self._call_single(obj)

    def _call_single(self, obj):
        objs = obj.split(":")
        call = self._special_calls(obj) #map(self._special_calls, objs)
        if call is None:
            try:
                call = self.__getattribute__(obj) #map(self.__getattribute__, objs)
            except AttributeError as e:
                call = None
        if call is None:
            try:
                call = self.__getitem__(obj) #map(self.__getitem__, objs)
            except KeyError as e:
                call = None
        #if isinstance(call, tuple):
        #    if len(call) == 1:
        #        return call[0]
        return call

    def api(self, query, parent=None):
        fltr, obj, args = self._break_into_parts(query)
        if fltr is not None:
            result = self._filter(fltr)
        elif obj is not None:
            result = self._call(obj)
        if hasattr(result, "api") and args and args != "/":
            return result.api(args)
        return result
    
class APICollection(APIObject,list):
    def __init__(self, data=[]):
        super(APICollection, self).__init__(data)

    def _reduce(self):
        return [item for sublist in self for item in sublist]

    def _call(self, obj):
        newlist = []
        for x in self:
            res = x._call_single(obj)
            if hasattr(res, "__iter__"):
                newlist.extend(res)
            else:
                newlist.append(res)
        return APICollection( newlist )

    def _filter(self, fltr):
        fltr = re.sub(match_comment, r"", fltr)
        fltr = re.sub(match_replace, r"x.api('\1')", fltr)
        newlist = []
        for x in self:
            if eval(fltr):
                newlist.append(x) 
        return APICollection(newlist)

class APIDict(APIObject,dict):
    def __init__(self, data={}):
        super(APIDict, self).__init__(data)

    def _special_calls(self, obj):
        if obj == "keys":
            return self.keys()

class APIFile(APIObject):
    pass

#======================================
# Some kim api wrapped things
#======================================

def valid_match(test,model):
    """ Test to see if a test and model match using the kim API, returns bool
        
        Tests through ``kimservice.KIM_API_init``, running in its own forked process    
    """
    #logger.debug("attempting to match %r with %r",testname,modelname)
    logger.debug("invoking KIMAPI for (%r,%r)",test,model)
    pid = os.fork()
    if (pid==0):
        logger.debug("in fork")
        match, pkim = kimservice.KIM_API_init(test.kim_code,model.kim_code)
        if match:
            kimservice.KIM_API_free(pkim)
            os._exit(0)
        os._exit(1)

    # try to get the exit code from the kim api process
    exitcode = os.waitpid(pid,0)[1]/256
    logger.debug("got exitcode: %r" , exitcode )
    if exitcode == 0:
        match = True
    elif exitcode == 1:
        match = False
    else:
        logger.error("We seem to have a Kim init error on (%r,%r)", test, model)
        raise KIMRuntimeError
        match = False

    if match:
        return True
    else:
        return False


