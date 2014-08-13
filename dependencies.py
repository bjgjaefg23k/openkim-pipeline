#! /usr/bin/env python
"""
The idea of these function is to get the immediate dependencies surrounding
this particular item that we have heard has been updated (is incoming on the
pipeline)

Note: there are two types of dependencies - static and runtime

* static - things that it must compile against / have on the file system in
    order to run properly (denoted sdeps)
* runtime - these are data / files drawn from other results / reference that
    are pulled in while running (denoted rdeps)

This is a kind of two sided mechanism in which both new objects and results of
computations both trigger update messages.  In this way, we can cut down on
tree-building and resolution before submitting.  It's a bit more robust and
free-form: just care about your neighbors.

If this is a test / model / test driver / model driver, then
the action is:

    * Get all runtime dependencies that this test result depends on
        - ignore the sdeps since they will be handled later
    * Check to see if the other dependencies are in place:
        - see if a particular result is at its latest.  if not, add that to
          the list of pairs to run (at higher priority) if it is not running
          already
        - if there are results outstanding, do not submit the original pair
          (since the acceptance of the test result will trigger it again)

If we are told that a new test result has come in:

    * Get all (te, mo) pairs that depend on this result
    * See if they need to be updated (are they latest?)
    * Send these updates through the original channels

Local dependency resolution
"""
import kimobjects
import kimquery

from logger import logging
logger = logging.getLogger("pipeline").getChild("dependencies")

def result_inqueue(test, model):
    query = {"database": "job", "test": str(test), "model": str(model),
             "project": ["tube"], "limit": 1}

    tube = kimquery.query(query, decode=True)
    return len(tube) > 0

def result_exists(test, model):
    query = {"project": ["uuid"], "database": "obj", "query":
                {
                    "runner.kimcode": str(test),
                    "subject.kimcode": str(model),
                },
            "limit": 1}

    result = kimquery.query(query, decode=True)
    return len(result) > 0

def result_pair(uuid):
    query = {"database": "obj", "limit": 1,
             "query": {"uuid": uuid},
             "project": ["runner.kimcode", "subject.kimcode"]}
    return (kimobjects.kim_obj(a) for a in kimquery.query(query, decode=True))

def list2obj(l):
    return (
        kimobjects.kim_obj(l[0], search=True),
        kimobjects.kim_obj(l[1], search=True)
    )

def get_run_list(target, depth=0, tree=False, display=False):
    if hasattr(target, '__iter__'):
        # we have a (test,model) pair which needs updating
        torun = set()
        satisfied = True

        te, mo = target
        deps = te.runtime_dependencies(mo)

        for dep in deps:
            if hasattr(dep, '__iter__'):
                tmp_te, tmp_mo = list2obj(dep)

                if not result_exists(tmp_te, tmp_mo):
                    # there are results that need be collected, wait for them
                    satisfied = False

                    if not result_inqueue(tmp_te, tmp_mo):
                        # they are not on the queue, let's get around to run
                        for dep in get_run_list((tmp_te, tmp_mo),
                                        depth=depth+1, display=display):
                            torun.add(dep)

        if satisfied:
            if not result_exists(te, mo):
                return [(te, mo)]
            logger.debug("Result exists for (%r, %r), skipping..." % (te, mo))
            return []
        return list(torun)

    else:
        # we have a test result that has come in
        te, mo = result_pair(target)

        torun = set()
        for test in kimobjects.Test.all():
            deps = test.runtime_dependencies(mo)

            for dep in deps:
                if hasattr(dep, '__iter__'):
                    tmpte, tmpmo = list2obj(dep)

                    if te == tmpte and mo == tmpmo:
                        for m in get_run_list((test,mo),
                                depth=depth+1, display=display):
                            torun.add(m)
        return list(torun)
