#! /usr/bin/env python
"""
dependencies.py handles the tracking of dependencies throughout the
repository and mongodb database.
"""
import simplejson

from config import *
import kimobjects
import kimquery
from database import RE_KIMID

from logger import logging
logger = logging.getLogger("pipeline").getChild("dependencies")

def dependency_check(inp, model=True):
    """ Given an input file
        find all of the data directives and obtain the pointers to the relevant data if it exists
        if it doesn't exist, return a false and a list of dependent tests

        outputs:
            ready - bool
            dependencies_good_to_go - list of kids
            dependencies_needed - tuple of tuples
    """
    logger.debug("running a dependancy check for %r", os.path.basename(os.path.dirname(inp.name)))
    ready, dependencies = (True, [])

    cands = []
    #try to find all of the possible dependencies
    for line in inp:
        matches = re.finditer(RE_KIMID, line)
        for match in matches:
            matched_code = match.string[match.start():match.end()]
            cands.append((True, kimobjects.kim_obj(matched_code)))

    if not cands:
        return (True, None, None)

    #cheap transpose
    candstranspose = zip(*cands)
    allready = all(candstranspose[0])

    if allready:
        return (allready, candstranspose[1], None)
    else:
        return (allready, 
                (kid for ready,kid in cands if ready), 
                (pair for ready, pair in cands if not ready))
