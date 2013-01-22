""" Contains some wrapped KIM_API calls,

    going through kimservice
"""

import os, sys, re
import kimservice
from config import *
from itertools import chain

logger = logger.getChild("repository")
#/(? stuff ?)/blah or /name_qualifier/blah
# match_args   = re.compile(
#     r"""
#     (?:^\(\?.*?\?\))? #filter group
#     (?:^[a-zA-Z0-9_\-]*?)? #object group
#     (\/.*) #everything else
#     """)

match_slash  = re.compile(r"^(\/)*(.*)")
match_filter = re.compile(r"^\(\:(.*?)\:\)(\/*.*)")
match_object = re.compile(r"^([a-zA-Z0-9_\-:]*)(\/*.*)")

#match_slash  = re.compile(
#    r"""
#    ^           #start of string
#    (\/)*       #match any number of starting backslashes
#    (.*)        # grab everything else
#    """)
## match_filter = re.compile(r"^\(\?(.*?)\?\)(\/*.*)")
#match_filter = re.compile(
#    r"""
#    ^\(\?       # if the string starts with ?
#    (.*?)       # grab the inards, non-greedy
#    \?\)        # the  matching ?
#    (\/*.*)     # rest of the expression
#    """)
#match_object = re.compile(
#    r"""
#    ^([a-zA-Z0-9_:]*)       # starts with a valid python name (or has :)
#    (\/*.*)                 # grab the rest of the query
#    """)

match_import  = r"import"     # get rid of imports
match_comment = r"(@#.*?#@)"  # used in re.sub to get rid of comments
match_replace = r"@@(.*?)@@"  # used in re.sub to substitute @@/apicall@@ -> x.api("/apicall")
match_index   = r"@\[(\d)\]@"  # FIXME - not implemented

#=======================================================
# the base APIObject which implements all standard calls
#=======================================================
class APIObject(object):
    """ The main api object.  Every api call should return
    one of these or a subclass of this
    """
    def api(self, query, parent=None):
        fltr, obj, args = self._break_into_parts(query)
        if fltr is not None:
            result = self._filter(fltr)
        elif obj is not None:
            result = self._call(obj)
        if hasattr(result, "api") and args and args != "/":
            return result.api(args)
        return result

    def _special_calls(self, arg0):
        """ The special api calls are caught here """
        pass

    def _break_into_parts(self, query):
        """ Parse the query, finding the first logical set in /s """
        # remove the leading slash
        query = match_slash.match(query).groups()[1]

        # find if there is a filter group or object group first
        grp_flt = match_filter.match(query)
        grp_obj = match_object.match(query)

        obj = fltr = None
        if grp_flt:
            # if there was a filter
            fltr, args = grp_flt.groups()
        else:
            # if there was an object
            obj, args = grp_obj.groups()
        return (fltr, obj, args)

    def _filter(self, fltr):
        """ a base case of filtering for one object which
        either returns the object or not
            fltr looks like '@#checks if it took more than a second#@  @@/_time@@ > 1' when it comes in
            removes the section from @# -> #@
            then replaces @@/_time@@ with 'self.api("/_time")'
            and evaluates the expression
        """
        fltr = re.sub(match_import, r"", fltr)
        fltr = re.sub(match_comment, r"", fltr)
        fltr = re.sub(match_replace, r"self.api('\1')", fltr)
        if eval(fltr):
            return self
        return None

    def _call(self, obj):
        return self._call_single(obj)

    def _call_single(self, obj):
        objs = obj.split(":")
        # call = self._special_calls(obj) or self.__getattribute__(obj) or self.__getitem__(obj)
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
            except AttributeError as e:
                call = None
        #if isinstance(call, tuple):
        #    if len(call) == 1:
        #        return call[0]
        return call

    @property
    def help(self):
        return "Not implemented"

def unique_everseen(iterable):
    known = {}
    for item in iterable:
        if item not in known:
            known.add(item)
            yield item

class APICollection(APIObject):
    """ A collection of api objects, meant to behave
    like a generator, supporting filtering """
    def __init__(self, iterable=None):
        super(APICollection, self).__init__()
        self.iterable = iter(iterable)

    def __iter__(self):
        return self.iterable

    def next(self):
        return next(self.iterable)

    def __getitem__(self,item):
        """ Pass item access onto to elements in collection """
        return APICollection( x.__getitem__(item) for x in self.iterable )

    def _wrap(self, iterable):
        """ Ensure we return an iter """
        if hasattr(iterable,'__iter__'):
            return iterable
        return [iterable]

    def _call(self, obj):
        """ Pass objects onto the elements in the collection,
            Use chain.from_iterable to ensure the collection stays flat,
            though this requires we wrap individual elements into iterable lists """
        call = None #self._call_single(obj)
        if call is None:
            call = APICollection(
                    chain.from_iterable(   #chain all results together
                        self._wrap(x._call_single(obj)) for x in self.iterable # wrap individuals in lists
                        )
                    )
        return call

    def _filter(self, fltr):
        """ Use objects to compute filters """
        return APICollection( x for x in self.iterable if x._filter(fltr) )

    def __str__(self):
        return str([ str(x) for x in self.iterable])

    #@property
    #def unique(self):
    #    return set(self.iterable)
    @property
    def unique(self):
        return APICollection(unique_everseen(self.iterable))



class APIDict(APIObject,dict):
    """ A special dict instance meant to be an APIObject """
    def __init__(self, *args, **kwargs):
        super(APIDict, self).__init__(*args, **kwargs)


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


