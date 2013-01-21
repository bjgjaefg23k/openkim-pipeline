"""
An attempt at making a nice api wrapper thing
that will look a bit like the website with
/s treating in sequence recursively.
"""

from persistentdict import PersistentDict

class APIObject(object):
    """ A valid API object """
    def _object_lookup(self,arg):
        if self._special_arg(arg):
           pass
       return self.__getattribute__(arg)

    def api(self,query):
        if not query:
            return self
        # get up to next /
        args = query.split('/')
        arg0 = args[0]
        nextquery = "/".join(args[1:])

        # find next object and pass
        return self._object_lookup(arg0).api(nextquery)

class KIMObject(APIObject):
    """ A kim object """


class KIMObjects(APIObject,list):
    """ a list of kim objects """

class JSONInfo(APIObject):
    """ A set of json information """

class PersistentDict(JSONInfo):
    """ needs to be special dicts of special dicts """

class FileObject(APIObject):
    """ a file """

class Test(KIMObject):
    """ A KIM Test """


